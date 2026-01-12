# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bhz_ai_llm_provider = fields.Selection([
        ("openai_compatible", "OpenAI-compatible"),
        ("ollama", "Ollama"),
    ], default="openai_compatible")

    bhz_ai_openai_base_url = fields.Char()
    bhz_ai_openai_api_key = fields.Char()
    bhz_ai_openai_model = fields.Char(default="gpt-4o-mini")

    bhz_ai_ollama_url = fields.Char(default="http://localhost:11434")
    bhz_ai_ollama_model = fields.Char(default="llama3.1")

    def set_values(self):
        super().set_values()
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("bhz_ai_org.llm_provider", self.bhz_ai_llm_provider or "openai_compatible")
        icp.set_param("bhz_ai_org.openai_base_url", self.bhz_ai_openai_base_url or "")
        icp.set_param("bhz_ai_org.openai_api_key", self.bhz_ai_openai_api_key or "")
        icp.set_param("bhz_ai_org.openai_model", self.bhz_ai_openai_model or "gpt-4o-mini")
        icp.set_param("bhz_ai_org.ollama_url", self.bhz_ai_ollama_url or "http://localhost:11434")
        icp.set_param("bhz_ai_org.ollama_model", self.bhz_ai_ollama_model or "llama3.1")

    def get_values(self):
        res = super().get_values()
        icp = self.env["ir.config_parameter"].sudo()
        res.update(
            bhz_ai_llm_provider=icp.get_param("bhz_ai_org.llm_provider", "openai_compatible"),
            bhz_ai_openai_base_url=icp.get_param("bhz_ai_org.openai_base_url", ""),
            bhz_ai_openai_api_key=icp.get_param("bhz_ai_org.openai_api_key", ""),
            bhz_ai_openai_model=icp.get_param("bhz_ai_org.openai_model", "gpt-4o-mini"),
            bhz_ai_ollama_url=icp.get_param("bhz_ai_org.ollama_url", "http://localhost:11434"),
            bhz_ai_ollama_model=icp.get_param("bhz_ai_org.ollama_model", "llama3.1"),
        )
        return res
