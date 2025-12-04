/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

class InboxComponent extends Component {
    setup() {
        super.setup?.();
        this._rpc = (route, params) => rpc(route, params || {});
        this.notification = this.env.services.notification;
        this.bus = this.env.services.bus_service;
        this.state = useState({
            conversations: [],
            currentConversationId: null,
            currentConversation: null,
            messages: [],
            composer: "",
            loadingConversations: false,
            loadingMessages: false,
        });

        onWillStart(async () => {
            await this.loadConversations();
            this._subscribeBus();
        });
    }

    async loadConversations() {
        this.state.loadingConversations = true;
        try {
            const result = await this._rpc("/bhz/wa/inbox/conversations", {});
            const list = result.conversations || [];
            this.state.conversations = list;
            if (!list.length) {
                this.state.currentConversationId = null;
                this.state.currentConversation = null;
                this.state.messages = [];
                return;
            }
            const desiredId = this.state.currentConversationId;
            let target = list.find((conv) => conv.id === desiredId);
            if (!target) {
                target = list[0];
            }
            await this.setCurrentConversation(target);
        } finally {
            this.state.loadingConversations = false;
        }
    }

    async setCurrentConversation(convOrId) {
        let conversation = convOrId;
        if (!conversation || typeof conversation !== "object") {
            conversation = this.state.conversations.find((c) => c.id === convOrId);
        }
        if (!conversation) {
            this.state.currentConversationId = null;
            this.state.currentConversation = null;
            this.state.messages = [];
            return;
        }
        this.state.currentConversationId = conversation.id;
        this.state.currentConversation = conversation;
        await this.loadMessages(conversation.id);
        await this._rpc("/bhz/wa/inbox/mark_read", { conversation_id: conversation.id });
    }

    async loadMessages(conversationId) {
        if (!conversationId) {
            this.state.messages = [];
            return;
        }
        this.state.loadingMessages = true;
        try {
            const result = await this._rpc("/bhz/wa/inbox/messages", {
                conversation_id: conversationId,
                limit: 80,
                offset: 0,
            });
            this.state.messages = result.messages || [];
            setTimeout(() => this._scrollToBottom(), 50);
        } finally {
            this.state.loadingMessages = false;
        }
    }

    async sendMessage(ev) {
        ev?.preventDefault();
        if (!this.state.composer || !this.state.currentConversationId) {
            return;
        }
        const payload = {
            conversation_id: this.state.currentConversationId,
            body: this.state.composer,
        };
        const result = await this._rpc("/bhz/wa/inbox/send_message", payload);
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
        return this.state.currentConversation;
    }
}

InboxComponent.template = "bhz_wa.InboxRoot";

registry.category("actions").add("bhz_wa_inbox_action", InboxComponent);

export default InboxComponent;
