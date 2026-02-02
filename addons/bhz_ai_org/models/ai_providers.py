# -*- coding: utf-8 -*-
import json
import ipaddress
import socket
from urllib.parse import urlparse

import requests
from odoo import api, models
from odoo.exceptions import UserError

class BhzAiProviders(models.AbstractModel):
    _name = "bhz.ai.providers"
    _description = "AI Providers (LLM/Web)"

    @api.model
    def llm_generate(self, agent, prompt, temperature=0.2):
        """Retorna texto do LLM. Implementação default: OpenAI-compat via endpoint."""
        icp = self.env["ir.config_parameter"].sudo()
        provider = agent.llm_provider
        if provider == "system":
            provider = icp.get_param("bhz_ai_org.llm_provider", "openai_compatible")

        if provider == "disabled":
            raise UserError("LLM desabilitado.")

        if provider == "openai_compatible":
            base_url = icp.get_param("bhz_ai_org.openai_base_url", "").strip()
            api_key = icp.get_param("bhz_ai_org.openai_api_key", "").strip()
            model = agent.model_name or icp.get_param("bhz_ai_org.openai_model", "gpt-4o-mini")
            if not base_url or not api_key:
                raise UserError("Configure o provider OpenAI-compatible em Configurações > BHZ AI Org.")

            url = base_url.rstrip("/") + "/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": agent.system_prompt or "Você é um assistente corporativo."},
                    {"role": "user", "content": prompt},
                ],
            }
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            if r.status_code >= 400:
                raise UserError(f"Erro LLM: {r.status_code} - {r.text[:300]}")
            data = r.json()
            return (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""

        if provider == "ollama":
            # Stub simples (ajuste para sua infra)
            ollama_url = icp.get_param("bhz_ai_org.ollama_url", "http://localhost:11434").strip()
            model = agent.model_name or icp.get_param("bhz_ai_org.ollama_model", "llama3.1")
            url = ollama_url.rstrip("/") + "/api/generate"
            payload = {"model": model, "prompt": (agent.system_prompt or "") + "\n\n" + prompt, "stream": False}
            r = requests.post(url, json=payload, timeout=60)
            if r.status_code >= 400:
                raise UserError(f"Erro Ollama: {r.status_code} - {r.text[:300]}")
            return (r.json() or {}).get("response", "") or ""

        raise UserError(f"Provider não suportado: {provider}")

    @api.model
    def web_search(self, agent, query, num_results=5):
        """Busca via SerpAPI com allowlist de domínios e bloqueio de IPs privados."""
        icp = self.env["ir.config_parameter"].sudo()
        serp_key = icp.get_param("bhz_ai_org.serpapi_key", "").strip()

        agent_rec = agent if hasattr(agent, "id") else self.env["bhz.ai.agent"].browse(agent)
        policy = agent_rec.policy_id
        allowlist_raw = (policy.web_allowlist_domains or "").strip() if policy else ""
        allowlist = [d.strip().lower() for d in allowlist_raw.splitlines() if d.strip()]
        block_private = bool(policy and policy.web_block_private_ips)

        if not serp_key:
            return {
                "query": query,
                "results": [],
                "note": "SerpAPI não configurada em Configurações > BHZ AI Org.",
            }

        if not query:
            return {"query": query, "results": [], "note": "Query vazia."}

        try:
            num = int(num_results)
        except Exception:
            num = 5
        num = max(1, min(num, 20))

        params = {
            "engine": "google",
            "q": query,
            "api_key": serp_key,
            "num": num,
        }

        try:
            resp = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("organic_results", []) or []
        except Exception as e:
            return {
                "query": query,
                "results": [],
                "note": f"Erro ao consultar SerpAPI: {e}",
            }

        cleaned = []
        for r in results:
            url = (r.get("link") or "").strip()
            title = r.get("title") or ""
            snippet = r.get("snippet") or r.get("snippet_highlighted_words") or ""

            if not url:
                continue

            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            if allowlist:
                host_l = hostname.lower()
                if not any(host_l == d or host_l.endswith("." + d) for d in allowlist):
                    continue

            if block_private and hostname:
                if self._is_private_host(hostname):
                    continue

            cleaned.append({
                "title": title,
                "url": url,
                "snippet": snippet if isinstance(snippet, str) else " ".join(snippet),
            })

        return {"query": query, "results": cleaned}

    @api.model
    def _is_private_host(self, hostname):
        """Bloqueia hosts privados/reservados."""
        try:
            # Se já for IP
            ip_obj = ipaddress.ip_address(hostname)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved
        except ValueError:
            pass

        try:
            infos = socket.getaddrinfo(hostname, None)
            for fam, _, _, _, sockaddr in infos:
                if fam in (socket.AF_INET, socket.AF_INET6):
                    ip_obj = ipaddress.ip_address(sockaddr[0])
                    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
                        return True
        except Exception:
            # Em dúvida, não bloqueia mas também não falha o fluxo
            return False
        return False
