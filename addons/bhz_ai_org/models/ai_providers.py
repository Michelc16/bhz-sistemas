# -*- coding: utf-8 -*-
import json
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
    def web_search(self, agent, query):
        """Stub de busca web. Ideal: integrar SerpAPI/Bing/Google CSE/etc com allowlist."""
        # Aqui você pluga seu provider real. Mantive stub para não “prometer” internet nativa.
        return {
            "query": query,
            "results": [],
            "note": "Web provider não configurado. Integre SerpAPI/Bing/CSE e aplique allowlist no policy.",
        }
