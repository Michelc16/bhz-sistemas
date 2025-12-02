/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

class InboxComponent extends Component {
    setup() {
        super.setup?.();
        this.rpc = this.env.services.rpc;
        this.notification = this.env.services.notification;
        this.bus = this.env.services.bus_service;
        this.state = useState({
            conversations: [],
            currentConversationId: null,
            messages: [],
            composer: "",
        });

        onWillStart(async () => {
            await this.loadConversations();
            this._subscribeBus();
        });
    }

    async loadConversations() {
        const result = await this.rpc("/bhz/wa/inbox/conversations", {});
        this.state.conversations = result.conversations || [];
        if (!this.state.currentConversationId && this.state.conversations.length) {
            const firstId = this.state.conversations[0].id;
            await this.setCurrentConversation(firstId);
        }
    }

    async setCurrentConversation(conversationId) {
        this.state.currentConversationId = conversationId;
        await this.loadMessages(conversationId);
        await this.rpc("/bhz/wa/inbox/mark_read", { conversation_id: conversationId });
    }

    async loadMessages(conversationId) {
        if (!conversationId) {
            this.state.messages = [];
            return;
        }
        const result = await this.rpc("/bhz/wa/inbox/messages", {
            conversation_id: conversationId,
            limit: 80,
            offset: 0,
        });
        this.state.messages = result.messages || [];
        setTimeout(() => this._scrollToBottom(), 50);
    }

    async sendMessage(ev) {
        ev?.preventDefault();
        if (!this.state.composer) {
            return;
        }
        const payload = {
            conversation_id: this.state.currentConversationId,
            body: this.state.composer,
        };
        const result = await this.rpc("/bhz/wa/inbox/send_message", payload);
        if (result.error) {
            this.notification.add(_t("Falha ao enviar mensagem"), { type: "danger" });
            return;
        }
        this.state.composer = "";
        if (result.message) {
            this.state.messages.push(result.message);
            setTimeout(() => this._scrollToBottom(), 30);
        }
        await this.loadConversations();
    }

    _scrollToBottom() {
        const area = this.el.querySelector('.bhz-wa-chat__messages');
        if (area) {
            area.scrollTop = area.scrollHeight;
        }
    }

    _subscribeBus() {
        this.bus.addChannel('bhz_wa_inbox');
        this.bus.start();
        this.bus.addEventListener('notification', (notifications) => {
            for (const notif of notifications) {
                const payload = notif.payload;
                if (payload?.type === 'new_message') {
                    this.loadConversations();
                    if (payload.conversation_id === this.state.currentConversationId) {
                        this.loadMessages(this.state.currentConversationId);
                    }
                }
            }
        });
    }

    get currentConversation() {
        return this.state.conversations.find((conv) => conv.id === this.state.currentConversationId);
    }
}

InboxComponent.template = "bhz_wa.InboxRoot";

registry.category("actions").add("bhz_wa_inbox_action", InboxComponent);

export default InboxComponent;
