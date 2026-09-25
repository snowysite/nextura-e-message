console.log("🔥 NEXTURA CHAT.JS LOADED");

(() => {
    "use strict";


    // =========================================================
    // USER / CHAT INFORMATION
    // =========================================================

    const senderId = Number(window.SENDER_ID);
    const receiverId = Number(window.RECEIVER_ID);

    console.log("👤 Sender ID:", senderId);
    console.log("👤 Receiver ID:", receiverId);


    // =========================================================
    // SOCKET.IO
    // =========================================================

    const socket =
        window.nexturaSocket ||
        (typeof io === "function" ? io() : null);

    if (!socket) {
        console.error("❌ Socket.IO is not available.");
        return;
    }

    console.log("✅ Socket.IO available");


    // =========================================================
    // CHAT ELEMENTS
    // =========================================================

    const chatForm =
        document.getElementById("chat-form");

    const chatInput =
        document.getElementById("chat-input");

    const chatBox =
        document.getElementById("chat-box");

    const sendMessageBtn =
        document.getElementById("send-message-btn");

    const emojiBtn =
        document.getElementById("emoji-btn");

    const emojiPicker =
        document.getElementById("emojiPicker");

    const emojiSearch =
        document.getElementById("emojiSearch");

    const emojiGrid =
        document.getElementById("emojiGrid");

    const voiceBtn =
        document.getElementById("voice-btn");

    const callBtn =
        document.getElementById("call-btn");

    const endCallBtn =
        document.getElementById("end-call-btn");

    const callStatus =
        document.getElementById("call-status");

    const incomingCall =
        document.getElementById("incoming-call");

    const acceptCallBtn =
        document.getElementById("accept-call");

    const rejectCallBtn =
        document.getElementById("reject-call");

    const remoteAudio =
        document.getElementById("remote-audio");

    const ringtone =
        document.getElementById("ringtone");

    const ringback =
        document.getElementById("ringback");


    // =========================================================
    // REPLY / EDIT COMPOSER
    // =========================================================

    const replyComposer =
        document.getElementById("reply-composer");

    const replyComposerLabel =
        document.getElementById("reply-composer-label");

    const replyComposerText =
        document.getElementById("reply-composer-text");

    const cancelReplyBtn =
        document.getElementById("cancel-reply");


    // =========================================================
    // REPLY STATE
    // =========================================================

    let replyToId = null;
    let replyToType = null;
    let replyToText = "";
    let replyToSenderName = "";


    // =========================================================
    // EDIT STATE
    // =========================================================

    let editingMessageId = null;
    let editingOriginalText = "";


    console.log("💬 Chat form:", chatForm);
    console.log("⌨️ Chat input:", chatInput);
    console.log("📦 Chat box:", chatBox);


    // =========================================================
    // JOIN CHAT ROOM
    // =========================================================

    function joinChatRoom() {

        if (!receiverId) {
            console.error("❌ Receiver ID is missing.");
            return;
        }

        socket.emit("join", {
            receiver_id: receiverId
        });

        console.log(
            "✅ Joined chat room with user:",
            receiverId
        );
    }


    socket.on("connect", () => {

        console.log(
            "✅ Socket connected:",
            socket.id
        );

        joinChatRoom();
    });


    if (socket.connected) {
        joinChatRoom();
    }


    // =========================================================
    // SCROLL CHAT
    // =========================================================

    function scrollChatToBottom() {

        if (!chatBox) {
            return;
        }

        chatBox.scrollTop =
            chatBox.scrollHeight;
    }


    // =========================================================
    // CLOSE ALL MESSAGE MENUS
    // =========================================================

    function closeAllMessageMenus(exceptMenu = null) {

        if (!chatBox) {
            return;
        }

        const menus =
            chatBox.querySelectorAll(
                ".message-menu.show"
            );

        menus.forEach(function (menu) {

            if (menu !== exceptMenu) {

                menu.classList.remove(
                    "show"
                );
            }
        });
    }


    // =========================================================
    // GET MESSAGE ELEMENT
    // =========================================================

    function getMessageElement(messageId) {

        if (!chatBox || !messageId) {
            return null;
        }

        return chatBox.querySelector(
            `[data-message-id="${messageId}"]`
        );
    }


    // =========================================================
    // GET MESSAGE ROW
    // =========================================================

    function getMessageRow(messageId) {

        const messageElement =
            getMessageElement(messageId);

        if (!messageElement) {
            return null;
        }

        return messageElement.closest(
            ".nextura-message-row"
        );
    }


    // =========================================================
    // GET MESSAGE TEXT
    // =========================================================

    function getTextFromMessageElement(messageElement) {

        if (!messageElement) {
            return "";
        }

        const textElement =
            messageElement.querySelector(
                ".message-text"
            );

        if (textElement) {
            return textElement.textContent || "";
        }

        return messageElement.dataset.messagePreview || "";
    }


    // =========================================================
    // REPLY HELPERS
    // =========================================================

    function getReplyPreviewText(data) {

        if (data.deleted_for_everyone) {
            return "🚫 This message was deleted";
        }

        if (
            data.message_type === "voice" ||
            data.audio
        ) {
            return "🎙 Voice message";
        }

        return data.message || "";
    }


    function clearReply() {

        replyToId = null;
        replyToType = null;
        replyToText = "";
        replyToSenderName = "";

        if (replyComposer) {

            replyComposer.classList.remove(
                "active"
            );

            replyComposer.classList.remove(
                "show"
            );

            replyComposer.classList.remove(
                "editing"
            );

            replyComposer.setAttribute(
                "aria-hidden",
                "true"
            );
        }

        if (replyComposerLabel) {

            replyComposerLabel.textContent =
                "Replying to";
        }

        if (replyComposerText) {

            replyComposerText.textContent =
                "";
        }
    }


    // =========================================================
    // START REPLY
    // =========================================================

    function startReply(messageElement) {

        if (!messageElement) {
            return;
        }

        if (
            messageElement.dataset.deletedForEveryone ===
            "1"
        ) {

            console.log(
                "🚫 Cannot reply to deleted message."
            );

            return;
        }


        if (editingMessageId) {
            cancelEditing();
        }


        const messageId =
            Number(
                messageElement.dataset.messageId
            );

        if (!messageId) {
            return;
        }


        const messageType =
            messageElement.dataset.messageType ||
            "text";


        let previewText =
            messageElement.dataset.messagePreview ||
            "";


        const senderName =
            messageElement.dataset.senderName ||
            "";


        if (
            !previewText &&
            messageType === "voice"
        ) {
            previewText =
                "🎙 Voice message";
        }


        replyToId = messageId;
        replyToType = messageType;
        replyToText = previewText;
        replyToSenderName = senderName;


        if (replyComposer) {

            replyComposer.classList.add(
                "show"
            );

            replyComposer.classList.add(
                "active"
            );

            replyComposer.classList.remove(
                "editing"
            );

            replyComposer.setAttribute(
                "aria-hidden",
                "false"
            );
        }


        if (replyComposerLabel) {

            replyComposerLabel.textContent =
                senderName
                    ? `Replying to ${senderName}`
                    : "Replying to";
        }


        if (replyComposerText) {

            replyComposerText.textContent =
                previewText;
        }


        if (chatInput) {
            chatInput.focus();
        }


        console.log(
            "↩️ Replying to message:",
            messageId
        );
    }


    // =========================================================
    // SCROLL TO MESSAGE
    // =========================================================

    function scrollToMessage(messageId) {

        if (!chatBox || !messageId) {
            return;
        }


        const target =
            getMessageElement(messageId);


        if (!target) {
            return;
        }


        target.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });


        target.classList.add(
            "reply-highlight"
        );


        setTimeout(function () {

            target.classList.remove(
                "reply-highlight"
            );

        }, 1500);
    }


    // =========================================================
    // START EDITING
    // =========================================================

    function startEditing(messageElement) {

        if (!messageElement) {
            return;
        }


        const messageId =
            Number(
                messageElement.dataset.messageId
            );


        if (!messageId) {
            return;
        }


        const messageType =
            messageElement.dataset.messageType ||
            "text";


        const messageSenderId =
            Number(
                messageElement.dataset.senderId
            );


        const deleted =
            messageElement.dataset.deletedForEveryone ===
            "1";


        // -----------------------------------------------------
        // SECURITY / VALIDATION
        // -----------------------------------------------------

        if (messageSenderId !== senderId) {

            console.log(
                "🚫 You can only edit your own messages."
            );

            return;
        }


        if (messageType === "voice") {

            console.log(
                "🚫 Voice messages cannot be edited."
            );

            return;
        }


        if (deleted) {

            console.log(
                "🚫 Deleted messages cannot be edited."
            );

            return;
        }


        // -----------------------------------------------------
        // Cancel reply first
        // -----------------------------------------------------

        replyToId = null;
        replyToType = null;
        replyToText = "";
        replyToSenderName = "";


        // -----------------------------------------------------
        // Get current message text
        // -----------------------------------------------------

        const currentText =
            getTextFromMessageElement(
                messageElement
            );


        editingMessageId =
            messageId;


        editingOriginalText =
            currentText;


        // -----------------------------------------------------
        // Show editing composer
        // -----------------------------------------------------

        if (replyComposer) {

            replyComposer.classList.add(
                "show"
            );

            replyComposer.classList.add(
                "editing"
            );

            replyComposer.setAttribute(
                "aria-hidden",
                "false"
            );
        }


        if (replyComposerLabel) {

            replyComposerLabel.textContent =
                "Editing message";
        }


        if (replyComposerText) {

            replyComposerText.textContent =
                currentText;
        }


        // -----------------------------------------------------
        // Load message into input
        // -----------------------------------------------------

        if (chatInput) {

            chatInput.value =
                currentText;

            chatInput.focus();

            try {

                chatInput.setSelectionRange(
                    chatInput.value.length,
                    chatInput.value.length
                );

            } catch (error) {}
        }


        // -----------------------------------------------------
        // Change send button appearance
        // -----------------------------------------------------

        updateComposerForEdit();


        // -----------------------------------------------------
        // Close menus
        // -----------------------------------------------------

        closeAllMessageMenus();


        // -----------------------------------------------------
        // Scroll message into view
        // -----------------------------------------------------

        messageElement.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });


        console.log(
            "✏️ Editing message:",
            messageId
        );
    }


    // =========================================================
    // UPDATE COMPOSER FOR EDIT MODE
    // =========================================================

    function updateComposerForEdit() {

        if (sendMessageBtn) {

            sendMessageBtn.innerHTML =
                '<i class="bi bi-check-lg"></i>';

            sendMessageBtn.title =
                "Save edited message";
        }


        if (chatInput) {

            chatInput.placeholder =
                "Edit message...";
        }


        if (voiceBtn) {

            voiceBtn.disabled =
                true;

            voiceBtn.style.opacity =
                "0.45";

            voiceBtn.title =
                "Voice messages cannot be used while editing";
        }
    }


    // =========================================================
    // UPDATE COMPOSER FOR NORMAL MODE
    // =========================================================

    function updateComposerForNormal() {

        if (sendMessageBtn) {

            sendMessageBtn.innerHTML =
                '<i class="bi bi-send-fill"></i>';

            sendMessageBtn.title =
                "Send message";
        }


        if (chatInput) {

            chatInput.placeholder =
                "Type a message...";
        }


        if (voiceBtn) {

            voiceBtn.disabled =
                false;

            voiceBtn.style.opacity =
                "";

            voiceBtn.title =
                "Voice message";
        }
    }


    // =========================================================
    // CANCEL EDITING
    // =========================================================

    function cancelEditing() {

        if (!editingMessageId) {
            return;
        }


        console.log(
            "❌ Cancelling edit:",
            editingMessageId
        );


        editingMessageId =
            null;


        editingOriginalText =
            "";


        if (chatInput) {
            chatInput.value = "";
        }


        clearReply();

        updateComposerForNormal();


        if (chatInput) {
            chatInput.focus();
        }
    }


    // =========================================================
    // SAVE EDITED MESSAGE
    // =========================================================

    function saveEditedMessage() {

        if (!editingMessageId) {
            return;
        }


        if (!chatInput) {
            return;
        }


        const newText =
            chatInput.value.trim();


        if (!newText) {

            alert(
                "Edited message cannot be empty."
            );

            return;
        }


        if (newText.length > 5000) {

            alert(
                "Message is too long. Maximum is 5000 characters."
            );

            return;
        }


        if (
            newText ===
            editingOriginalText
        ) {

            cancelEditing();

            return;
        }


        console.log(
            "💾 Saving edited message:",
            editingMessageId
        );


        socket.emit(
            "edit_message",
            {
                message_id:
                    editingMessageId,

                message:
                    newText
            }
        );


        // -----------------------------------------------------
        // Do NOT immediately change the bubble.
        //
        // The backend sends message_edited to both users.
        // This keeps both clients synchronized.
        // -----------------------------------------------------
    }


    // =========================================================
    // CREATE REPLY PREVIEW
    // =========================================================

    function createReplyPreview(data, isMine) {

        if (!data.reply_to_id) {
            return null;
        }


        const preview =
            document.createElement("div");


        preview.className =
            "message-reply-preview";


        preview.dataset.replyTarget =
            String(data.reply_to_id);


        const name =
            document.createElement("span");


        name.className =
            "reply-preview-name";


        if (data.reply_sender_name) {

            name.textContent =
                data.reply_sender_name;

        } else {

            name.textContent =
                isMine
                    ? "You"
                    : "Replied message";
        }


        const text =
            document.createElement("span");


        text.className =
            "reply-preview-text";


        text.textContent =
            data.reply_preview ||
            getReplyPreviewText(
                data.reply_to_message ||
                data
            ) ||
            "Message";


        preview.appendChild(name);

        preview.appendChild(text);


        preview.addEventListener(
            "click",
            function (event) {

                event.stopPropagation();

                scrollToMessage(
                    Number(data.reply_to_id)
                );
            }
        );


        return preview;
    }


    // =========================================================
    // CREATE REPLY BUTTON
    // =========================================================

    function createReplyButton(messageData) {

        const button =
            document.createElement("button");


        button.type =
            "button";


        button.className =
            "reply-message-btn";


        button.dataset.messageId =
            String(messageData.id);


        button.dataset.messageType =
            messageData.message_type ||
            "text";


        button.title =
            "Reply";


        button.innerHTML =
            '<i class="bi bi-reply-fill"></i>';


        button.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                event.stopPropagation();


                const wrapper =
                    button.closest(
                        ".nextura-message-wrapper"
                    );


                const messageElement =
                    wrapper
                        ?.querySelector(
                            ".chat-bubble"
                        );


                startReply(
                    messageElement
                );
            }
        );


        return button;
    }


    // =========================================================
    // CREATE MESSAGE MENU
    // =========================================================

    function createMessageMenu(messageData, isMine) {

        const menu =
            document.createElement("div");


        menu.className =
            "message-menu";


        menu.dataset.menuMessageId =
            String(messageData.id);


        // -----------------------------------------------------
        // EDIT
        // -----------------------------------------------------

        if (
            isMine &&
            messageData.message_type !== "voice" &&
            !messageData.deleted_for_everyone
        ) {

            const editButton =
                document.createElement("button");


            editButton.type =
                "button";


            editButton.className =
                "edit-message-btn";


            editButton.dataset.messageId =
                String(messageData.id);


            editButton.innerHTML =
                `
                    <i class="bi bi-pencil-square"></i>
                    <span>Edit</span>
                `;


            editButton.addEventListener(
                "click",
                function (event) {

                    event.preventDefault();

                    event.stopPropagation();

                    closeAllMessageMenus();

                    const messageElement =
                        getMessageElement(
                            Number(
                                messageData.id
                            )
                        );


                    startEditing(
                        messageElement
                    );
                }
            );


            menu.appendChild(
                editButton
            );
        }


        // -----------------------------------------------------
        // DELETE FOR ME
        // -----------------------------------------------------

        const deleteForMe =
            document.createElement("button");


        deleteForMe.type =
            "button";


        deleteForMe.className =
            "delete-for-me-btn";


        deleteForMe.dataset.messageId =
            String(messageData.id);


        deleteForMe.innerHTML =
            `
                <i class="bi bi-trash"></i>
                <span>Delete for me</span>
            `;


        deleteForMe.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                event.stopPropagation();

                closeAllMessageMenus();

                requestDeleteForMe(
                    Number(messageData.id)
                );
            }
        );


        menu.appendChild(
            deleteForMe
        );


        // -----------------------------------------------------
        // DELETE FOR EVERYONE
        // -----------------------------------------------------

        if (
            isMine &&
            !messageData.deleted_for_everyone
        ) {

            const deleteForEveryone =
                document.createElement("button");


            deleteForEveryone.type =
                "button";


            deleteForEveryone.className =
                "delete-everyone delete-for-everyone-btn";


            deleteForEveryone.dataset.messageId =
                String(messageData.id);


            deleteForEveryone.innerHTML =
                `
                    <i class="bi bi-trash3-fill"></i>
                    <span>Delete for everyone</span>
                `;


            deleteForEveryone.addEventListener(
                "click",
                function (event) {

                    event.preventDefault();

                    event.stopPropagation();

                    closeAllMessageMenus();

                    requestDeleteForEveryone(
                        Number(messageData.id)
                    );
                }
            );


            menu.appendChild(
                deleteForEveryone
            );
        }


        return menu;
    }


    // =========================================================
    // CREATE MESSAGE ACTIONS
    // =========================================================

    function createMessageActions(messageData, isMine) {

        const actions =
            document.createElement("div");


        actions.className =
            "message-actions";


        // -----------------------------------------------------
        // REPLY
        // -----------------------------------------------------

        if (!messageData.deleted_for_everyone) {

            const replyButton =
                createReplyButton(
                    messageData
                );


            actions.appendChild(
                replyButton
            );
        }


        // -----------------------------------------------------
        // THREE DOT MENU
        // -----------------------------------------------------

        const menuButton =
            document.createElement("button");


        menuButton.type =
            "button";


        menuButton.className =
            "message-menu-btn";


        menuButton.dataset.messageId =
            String(messageData.id);


        menuButton.title =
            "Message options";


        menuButton.innerHTML =
            '<i class="bi bi-three-dots-vertical"></i>';


        const menu =
            createMessageMenu(
                messageData,
                isMine
            );


        menuButton.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                event.stopPropagation();


                const wasOpen =
                    menu.classList.contains(
                        "show"
                    );


                closeAllMessageMenus(
                    wasOpen
                        ? null
                        : menu
                );


                if (!wasOpen) {

                    menu.classList.add(
                        "show"
                    );
                }
            }
        );


        actions.appendChild(
            menuButton
        );


        actions.appendChild(
            menu
        );


        return actions;
    }


    // =========================================================
    // APPEND MESSAGE
    // =========================================================

    function appendMessage(data) {

        if (!chatBox) {
            return;
        }


        const messageSenderId =
            Number(data.sender_id);


        const messageReceiverId =
            Number(data.receiver_id);


        const isMine =
            messageSenderId === senderId;


        // -----------------------------------------------------
        // Prevent duplicates
        // -----------------------------------------------------

        if (data.id) {

            const existingMessage =
                getMessageElement(
                    data.id
                );


            if (existingMessage) {
                return;
            }
        }


        const wrapper =
            document.createElement("div");


        wrapper.className =
            isMine
                ? "d-flex justify-content-end mb-2 nextura-message-row sent"
                : "d-flex justify-content-start mb-2 nextura-message-row received";


        wrapper.dataset.messageRowId =
            data.id
                ? String(data.id)
                : "";


        const messageWrapper =
            document.createElement("div");


        messageWrapper.className =
            "nextura-message-wrapper";


        messageWrapper.style.maxWidth =
            "75%";


        const bubble =
            document.createElement("div");


        bubble.className =
            isMine
                ? "chat-bubble me"
                : "chat-bubble other";


        bubble.dataset.messageId =
            data.id
                ? String(data.id)
                : "";


        bubble.dataset.senderId =
            String(messageSenderId);


        bubble.dataset.receiverId =
            String(messageReceiverId);


        bubble.dataset.messageType =
            data.message_type ||
            "text";


        bubble.dataset.messagePreview =
            getReplyPreviewText(data);


        bubble.dataset.senderName =
            data.sender_name ||
            (isMine ? "You" : "");


        bubble.dataset.deletedForEveryone =
            data.deleted_for_everyone
                ? "1"
                : "0";


        bubble.dataset.edited =
            data.edited
                ? "1"
                : "0";


        // =====================================================
        // DELETED-FOR-EVERYONE
        // =====================================================

        if (data.deleted_for_everyone) {

            bubble.classList.add(
                "deleted-bubble"
            );


            const deleted =
                document.createElement("div");


            deleted.className =
                "deleted-message";


            const icon =
                document.createElement("i");


            icon.className =
                "bi bi-slash-circle";


            const span =
                document.createElement("span");


            span.textContent =
                "This message was deleted";


            deleted.appendChild(icon);
            deleted.appendChild(span);


            bubble.appendChild(
                deleted
            );

        }

        // =====================================================
        // NORMAL MESSAGE
        // =====================================================

        else {

            // -------------------------------------------------
            // REPLY PREVIEW
            // -------------------------------------------------

            const replyPreview =
                createReplyPreview(
                    data,
                    isMine
                );


            if (replyPreview) {

                bubble.appendChild(
                    replyPreview
                );
            }


            // -------------------------------------------------
            // VOICE
            // -------------------------------------------------

            if (
                data.message_type === "voice" ||
                data.audio
            ) {

                const audio =
                    document.createElement("audio");


                audio.controls =
                    true;


                audio.preload =
                    "metadata";


                audio.style.maxWidth =
                    "240px";


                if (data.audio) {

                    audio.src =
                        data.audio;

                } else if (data.message) {

                    audio.src =
                        "/static/uploads/voices/" +
                        data.message;
                }


                bubble.appendChild(
                    audio
                );

            }

            // -------------------------------------------------
            // TEXT
            // -------------------------------------------------

            else {

                const text =
                    document.createElement("span");


                text.className =
                    "message-text";


                text.textContent =
                    data.message || "";


                bubble.appendChild(
                    text
                );


                if (data.edited) {

                    addEditedIndicator(
                        bubble
                    );
                }
            }


            // -------------------------------------------------
            // MESSAGE STATUS
            // -------------------------------------------------

            if (isMine) {

                const status =
                    document.createElement("small");


                status.className =
                    "message-status";


                status.textContent =
                    " ✓✓";


                status.style.marginLeft =
                    "6px";


                status.style.opacity =
                    "0.7";


                bubble.appendChild(
                    status
                );
            }
        }


        // =====================================================
        // MESSAGE ACTIONS
        // =====================================================

        if (data.id) {

            const actions =
                createMessageActions(
                    data,
                    isMine
                );


            messageWrapper.appendChild(
                bubble
            );


            messageWrapper.appendChild(
                actions
            );

        } else {

            messageWrapper.appendChild(
                bubble
            );
        }


        wrapper.appendChild(
            messageWrapper
        );


        chatBox.appendChild(
            wrapper
        );


        scrollChatToBottom();
    }


    // =========================================================
    // ADD EDITED INDICATOR
    // =========================================================

    function addEditedIndicator(bubble) {

        if (!bubble) {
            return;
        }


        const existing =
            bubble.querySelector(
                ".edited-indicator"
            );


        if (existing) {
            return;
        }


        const indicator =
            document.createElement("span");


        indicator.className =
            "edited-indicator";


        indicator.textContent =
            "edited";


        bubble.appendChild(
            indicator
        );
    }


    // =========================================================
    // UPDATE REPLY PREVIEWS
    // =========================================================

    function updateReplyPreviews(
        messageId,
        newText
    ) {

        if (!chatBox) {
            return;
        }


        const previews =
            chatBox.querySelectorAll(
                `.message-reply-preview[data-reply-target="${messageId}"]`
            );


        previews.forEach(
            function (preview) {

                const text =
                    preview.querySelector(
                        ".reply-preview-text"
                    );


                if (text) {

                    text.textContent =
                        newText;
                }
            }
        );
    }


    // =========================================================
    // UPDATE EDITED MESSAGE IN DOM
    // =========================================================

    function updateEditedMessage(data) {

        const messageId =
            Number(
                data.message_id ||
                data.id
            );


        if (!messageId) {
            return;
        }


        const messageElement =
            getMessageElement(
                messageId
            );


        if (!messageElement) {
            return;
        }


        // -----------------------------------------------------
        // Security: only text
        // -----------------------------------------------------

        if (
            messageElement.dataset.messageType !==
            "text"
        ) {
            return;
        }


        // -----------------------------------------------------
        // Get new text
        // -----------------------------------------------------

        const newText =
            String(
                data.message !== undefined
                    ? data.message
                    : data.text !== undefined
                        ? data.text
                        : ""
            );


        // -----------------------------------------------------
        // Update data
        // -----------------------------------------------------

        messageElement.dataset.edited =
            "1";


        messageElement.dataset.messagePreview =
            newText;


        // -----------------------------------------------------
        // Find/create message text
        // -----------------------------------------------------

        let textElement =
            messageElement.querySelector(
                ".message-text"
            );


        if (!textElement) {

            textElement =
                document.createElement("span");

            textElement.className =
                "message-text";

            messageElement.appendChild(
                textElement
            );
        }


        // textContent prevents HTML injection.
        textElement.textContent =
            newText;


        // -----------------------------------------------------
        // Remove old edited indicator
        // -----------------------------------------------------

        const oldIndicator =
            messageElement.querySelector(
                ".edited-indicator"
            );


        if (oldIndicator) {

            oldIndicator.remove();
        }


        // -----------------------------------------------------
        // Add edited indicator
        // -----------------------------------------------------

        addEditedIndicator(
            messageElement
        );


        // -----------------------------------------------------
        // Update reply previews
        // -----------------------------------------------------

        updateReplyPreviews(
            messageId,
            newText
        );


        // -----------------------------------------------------
        // Update reply-preview data of this message
        // -----------------------------------------------------

        const replyPreview =
            messageElement.querySelector(
                ".message-reply-preview"
            );


        // Nothing else required here.
        // The message itself now carries the new preview.
        void replyPreview;


        console.log(
            "✅ Message updated:",
            messageId
        );
    }


    // =========================================================
    // MESSAGE EDITED EVENT
    // =========================================================

    socket.on(
        "message_edited",
        function (data) {

            console.log(
                "✏️ message_edited:",
                data
            );


            const messageId =
                Number(
                    data.message_id ||
                    data.id
                );


            if (!messageId) {
                return;
            }


            updateEditedMessage(
                data
            );


            // -------------------------------------------------
            // If this is the user who initiated the edit,
            // clear edit mode after server confirmation.
            // -------------------------------------------------

            if (
                editingMessageId ===
                messageId
            ) {

                editingMessageId =
                    null;


                editingOriginalText =
                    "";


                if (chatInput) {

                    chatInput.value =
                        "";
                }


                clearReply();

                updateComposerForNormal();


                if (chatInput) {
                    chatInput.focus();
                }
            }
        }
    );


    // =========================================================
    // EXISTING SERVER-SIDE REPLY BUTTONS
    // =========================================================

    function initializeExistingReplyButtons() {

        if (!chatBox) {
            return;
        }


        const buttons =
            chatBox.querySelectorAll(
                ".reply-message-btn"
            );


        buttons.forEach(
            function (button) {

                if (
                    button.dataset.replyInitialized ===
                    "true"
                ) {
                    return;
                }


                button.dataset.replyInitialized =
                    "true";


                button.addEventListener(
                    "click",
                    function (event) {

                        event.preventDefault();

                        event.stopPropagation();


                        const wrapper =
                            button.closest(
                                ".nextura-message-wrapper"
                            );


                        const messageElement =
                            wrapper
                                ?.querySelector(
                                    ".chat-bubble"
                                );


                        startReply(
                            messageElement
                        );
                    }
                );
            }
        );


        const previews =
            chatBox.querySelectorAll(
                ".message-reply-preview"
            );


        previews.forEach(
            function (preview) {

                if (
                    preview.dataset.clickInitialized ===
                    "true"
                ) {
                    return;
                }


                preview.dataset.clickInitialized =
                    "true";


                preview.addEventListener(
                    "click",
                    function (event) {

                        event.preventDefault();

                        event.stopPropagation();


                        const targetId =
                            Number(
                                preview.dataset.replyTarget
                            );


                        scrollToMessage(
                            targetId
                        );
                    }
                );
            }
        );
    }


    // =========================================================
    // EXISTING MESSAGE MENUS
    // =========================================================

    function initializeExistingMessageMenus() {

        if (!chatBox) {
            return;
        }


        // -----------------------------------------------------
        // MENU BUTTONS
        // -----------------------------------------------------

        const menuButtons =
            chatBox.querySelectorAll(
                ".message-menu-btn"
            );


        menuButtons.forEach(
            function (button) {

                if (
                    button.dataset.menuInitialized ===
                    "true"
                ) {
                    return;
                }


                button.dataset.menuInitialized =
                    "true";


                const menu =
                    button
                        .closest(
                            ".message-actions"
                        )
                        ?.querySelector(
                            ".message-menu"
                        );


                if (!menu) {
                    return;
                }


                button.addEventListener(
                    "click",
                    function (event) {

                        event.preventDefault();

                        event.stopPropagation();


                        const wasOpen =
                            menu.classList.contains(
                                "show"
                            );


                        closeAllMessageMenus(
                            wasOpen
                                ? null
                                : menu
                        );


                        if (!wasOpen) {

                            menu.classList.add(
                                "show"
                            );
                        }
                    }
                );
            }
        );


        // -----------------------------------------------------
        // EDIT BUTTONS
        // -----------------------------------------------------

        const editButtons =
            chatBox.querySelectorAll(
                ".edit-message-btn"
            );


        editButtons.forEach(
            function (button) {

                if (
                    button.dataset.editInitialized ===
                    "true"
                ) {
                    return;
                }


                button.dataset.editInitialized =
                    "true";


                button.addEventListener(
                    "click",
                    function (event) {

                        event.preventDefault();

                        event.stopPropagation();


                        closeAllMessageMenus();


                        const messageId =
                            Number(
                                button.dataset.messageId
                            );


                        const messageElement =
                            getMessageElement(
                                messageId
                            );


                        startEditing(
                            messageElement
                        );
                    }
                );
            }
        );


        // -----------------------------------------------------
        // DELETE FOR ME
        // -----------------------------------------------------

        const deleteForMeButtons =
            chatBox.querySelectorAll(
                ".delete-for-me-btn"
            );


        deleteForMeButtons.forEach(
            function (button) {

                if (
                    button.dataset.deleteInitialized ===
                    "true"
                ) {
                    return;
                }


                button.dataset.deleteInitialized =
                    "true";


                button.addEventListener(
                    "click",
                    function (event) {

                        event.preventDefault();

                        event.stopPropagation();


                        closeAllMessageMenus();


                        const messageId =
                            Number(
                                button.dataset.messageId
                            );


                        requestDeleteForMe(
                            messageId
                        );
                    }
                );
            }
        );


        // -----------------------------------------------------
        // DELETE FOR EVERYONE
        // -----------------------------------------------------

        const deleteForEveryoneButtons =
            chatBox.querySelectorAll(
                ".delete-for-everyone-btn"
            );


        deleteForEveryoneButtons.forEach(
            function (button) {

                if (
                    button.dataset.deleteInitialized ===
                    "true"
                ) {
                    return;
                }


                button.dataset.deleteInitialized =
                    "true";


                button.addEventListener(
                    "click",
                    function (event) {

                        event.preventDefault();

                        event.stopPropagation();


                        closeAllMessageMenus();


                        const messageId =
                            Number(
                                button.dataset.messageId
                            );


                        requestDeleteForEveryone(
                            messageId
                        );
                    }
                );
            }
        );
    }


    initializeExistingReplyButtons();

    initializeExistingMessageMenus();


    // =========================================================
    // DELETE CONFIRMATION
    // =========================================================

    function requestDeleteForMe(messageId) {

        if (!messageId) {
            return;
        }


        const confirmed =
            window.confirm(
                "Delete this message for you?"
            );


        if (!confirmed) {
            return;
        }


        if (
            Number(editingMessageId) ===
            Number(messageId)
        ) {
            cancelEditing();
        }


        console.log(
            "🗑️ Deleting message for me:",
            messageId
        );


        socket.emit(
            "delete_message",
            {
                message_id:
                    messageId,

                delete_type:
                    "me"
            }
        );
    }


    function requestDeleteForEveryone(messageId) {

        if (!messageId) {
            return;
        }


        const confirmed =
            window.confirm(
                "Delete this message for everyone?"
            );


        if (!confirmed) {
            return;
        }


        if (
            Number(editingMessageId) ===
            Number(messageId)
        ) {
            cancelEditing();
        }


        console.log(
            "🗑️ Deleting message for everyone:",
            messageId
        );


        socket.emit(
            "delete_message",
            {
                message_id:
                    messageId,

                delete_type:
                    "everyone"
            }
        );
    }


    // =========================================================
    // DELETE FOR ME
    // =========================================================

    socket.on(
        "message_deleted_for_me",
        function (data) {

            console.log(
                "🗑️ message_deleted_for_me:",
                data
            );


            const messageId =
                Number(
                    data.message_id ||
                    data.id
                );


            if (!messageId) {
                return;
            }


            const row =
                getMessageRow(
                    messageId
                );


            if (!row) {
                return;
            }


            if (
                Number(replyToId) ===
                messageId
            ) {

                clearReply();
            }


            if (
                Number(editingMessageId) ===
                messageId
            ) {

                cancelEditing();
            }


            row.style.opacity =
                "0";


            row.style.transform =
                "translateX(10px)";


            row.style.transition =
                "opacity 0.2s ease, transform 0.2s ease";


            setTimeout(
                function () {

                    row.remove();

                },
                220
            );


            console.log(
                "✅ Message removed for current user."
            );
        }
    );


    // =========================================================
    // DELETE FOR EVERYONE
    // =========================================================

    socket.on(
        "message_deleted_for_everyone",
        function (data) {

            console.log(
                "🗑️ message_deleted_for_everyone:",
                data
            );


            const messageId =
                Number(
                    data.message_id ||
                    data.id
                );


            if (!messageId) {
                return;
            }


            const messageElement =
                getMessageElement(
                    messageId
                );


            if (!messageElement) {
                return;
            }


            if (
                Number(replyToId) ===
                messageId
            ) {

                clearReply();
            }


            if (
                Number(editingMessageId) ===
                messageId
            ) {

                cancelEditing();
            }


            // -------------------------------------------------
            // Mark deleted
            // -------------------------------------------------

            messageElement.dataset.deletedForEveryone =
                "1";


            messageElement.classList.add(
                "deleted-bubble"
            );


            // -------------------------------------------------
            // Stop audio
            // -------------------------------------------------

            const audio =
                messageElement.querySelector(
                    "audio"
                );


            if (audio) {

                audio.pause();

                audio.removeAttribute(
                    "src"
                );

                audio.load();
            }


            // -------------------------------------------------
            // Replace content
            // -------------------------------------------------

            messageElement.innerHTML =
                "";


            const deleted =
                document.createElement("div");


            deleted.className =
                "deleted-message";


            const icon =
                document.createElement("i");


            icon.className =
                "bi bi-slash-circle";


            const text =
                document.createElement("span");


            text.textContent =
                "This message was deleted";


            deleted.appendChild(icon);
            deleted.appendChild(text);


            messageElement.appendChild(
                deleted
            );


            // -------------------------------------------------
            // Disable reply
            // -------------------------------------------------

            const actions =
                messageElement
                    .closest(
                        ".nextura-message-wrapper"
                    )
                    ?.querySelector(
                        ".message-actions"
                    );


            if (actions) {

                const replyButton =
                    actions.querySelector(
                        ".reply-message-btn"
                    );


                if (replyButton) {

                    replyButton.remove();
                }


                const editButton =
                    actions.querySelector(
                        ".edit-message-btn"
                    );


                if (editButton) {

                    editButton.remove();
                }


                const deleteEveryoneButton =
                    actions.querySelector(
                        ".delete-for-everyone-btn"
                    );


                if (deleteEveryoneButton) {

                    deleteEveryoneButton.remove();
                }
            }


            // -------------------------------------------------
            // Update any reply previews
            // -------------------------------------------------

            updateReplyPreviews(
                messageId,
                "🚫 This message was deleted"
            );


            console.log(
                "✅ Message changed to deleted placeholder."
            );
        }
    );


    // =========================================================
    // CLOSE MESSAGE MENUS WHEN CLICKING OUTSIDE
    // =========================================================

    document.addEventListener(
        "click",
        function (event) {

            if (
                event.target.closest(
                    ".message-actions"
                )
            ) {
                return;
            }


            closeAllMessageMenus();
        }
    );


    // =========================================================
    // CANCEL REPLY / EDIT
    // =========================================================

    if (cancelReplyBtn) {

        cancelReplyBtn.addEventListener(
            "click",
            function (event) {

                event.preventDefault();


                if (editingMessageId) {

                    cancelEditing();

                } else {

                    clearReply();

                    if (chatInput) {
                        chatInput.focus();
                    }
                }
            }
        );
    }


    // =========================================================
    // SEND / EDIT TEXT MESSAGE
    // =========================================================

    if (chatForm) {

        chatForm.addEventListener(
            "submit",
            function (event) {

                event.preventDefault();
                event.stopPropagation();


                console.log(
                    "📤 Send button pressed"
                );


                if (!chatInput) {

                    console.error(
                        "❌ #chat-input was not found."
                    );

                    return;
                }


                // =================================================
                // EDIT MODE
                // =================================================

                if (editingMessageId) {

                    saveEditedMessage();

                    return;
                }


                // =================================================
                // NORMAL SEND MODE
                // =================================================

                const message =
                    chatInput.value.trim();


                if (!message) {
                    return;
                }


                if (!receiverId) {

                    console.error(
                        "❌ Receiver ID is missing."
                    );

                    return;
                }


                console.log(
                    "📤 Sending message:",
                    message
                );


                const payload = {

                    receiver_id:
                        receiverId,

                    message:
                        message
                };


                if (replyToId) {

                    payload.reply_to_id =
                        replyToId;
                }


                socket.emit(
                    "send_message",
                    payload
                );


                chatInput.value = "";


                clearReply();


                chatInput.focus();
            }
        );

    } else {

        console.error(
            "❌ #chat-form was not found."
        );
    }


    // =========================================================
    // RECEIVE TEXT / VOICE MESSAGE
    // =========================================================

    socket.on(
        "receive_message",
        function (data) {

            console.log(
                "📩 receive_message:",
                data
            );


            const messageSender =
                Number(data.sender_id);


            const messageReceiver =
                Number(data.receiver_id);


            const belongsToChat =
                (
                    messageSender === senderId &&
                    messageReceiver === receiverId
                ) ||
                (
                    messageSender === receiverId &&
                    messageReceiver === senderId
                );


            if (!belongsToChat) {
                return;
            }


            appendMessage(data);
        }
    );


    // =========================================================
    // SUPPORT new_message EVENT
    // =========================================================

    socket.on(
        "new_message",
        function (data) {

            console.log(
                "📩 new_message:",
                data
            );


            const messageSender =
                Number(data.sender_id);


            const messageReceiver =
                Number(data.receiver_id);


            const belongsToChat =
                (
                    messageSender === senderId &&
                    messageReceiver === receiverId
                ) ||
                (
                    messageSender === receiverId &&
                    messageReceiver === senderId
                );


            if (!belongsToChat) {
                return;
            }


            appendMessage(data);
        }
    );


    // =========================================================
    // EMOJI LIST
    // =========================================================

    const emojis = [

        "😀",
        "😃",
        "😄",
        "😁",
        "😆",
        "😅",
        "😂",
        "🤣",
        "😊",
        "😇",
        "🙂",
        "🙃",
        "😉",
        "😌",
        "😍",
        "🥰",
        "😘",
        "😗",
        "😙",
        "😚",
        "😋",
        "😛",
        "😝",
        "😜",
        "🤪",
        "🤨",
        "🧐",
        "🤓",
        "😎",
        "🥳",
        "🤩",
        "😏",
        "😒",
        "😞",
        "😔",
        "😟",
        "😕",
        "🙁",
        "☹️",
        "😣",
        "😖",
        "😫",
        "😩",
        "🥺",
        "😢",
        "😭",
        "😤",
        "😠",
        "😡",
        "🤬",
        "🤯",
        "😳",
        "🥵",
        "🥶",
        "😱",
        "😨",
        "😰",
        "😥",
        "😓",
        "🤗",
        "🤔",
        "🤭",
        "🤫",
        "🤥",
        "😶",
        "😐",
        "😑",
        "😬",
        "🙄",
        "😯",
        "😦",
        "😧",
        "😮",
        "😲",
        "🥱",
        "😴",
        "🤤",
        "😪",
        "😵",
        "🤐",
        "🤢",
        "🤮",
        "🤧",
        "😷",
        "🤒",
        "🤕",

        "❤️",
        "🧡",
        "💛",
        "💚",
        "💙",
        "💜",
        "🖤",
        "🤍",
        "🤎",
        "💔",
        "💕",
        "💞",
        "💓",
        "💗",
        "💖",
        "💘",
        "💝",

        "💯",
        "🔥",
        "✨",
        "⭐",
        "🌟",

        "👍",
        "👎",
        "👏",
        "🙌",
        "🙏",
        "👌",
        "✌️",
        "🤞",
        "🤝",
        "👋",
        "💪",
        "🎉",
        "🎊",
        "❤️‍🔥"
    ];


    // =========================================================
    // RENDER EMOJIS
    // =========================================================

    function renderEmojis() {

        if (!emojiGrid) {
            return;
        }


        emojiGrid.innerHTML = "";


        const searchTerm =
            emojiSearch
                ? emojiSearch.value
                    .trim()
                    .toLowerCase()
                : "";


        emojis.forEach(
            function (emoji) {

                /*
                 * Emoji characters themselves cannot really be
                 * searched by normal text, so an empty search
                 * displays everything.
                 *
                 * We preserve the existing picker behavior.
                 */

                if (
                    searchTerm &&
                    !emoji.includes(searchTerm)
                ) {
                    return;
                }


                const button =
                    document.createElement("button");


                button.type =
                    "button";


                button.className =
                    "emoji-item";


                button.textContent =
                    emoji;


                button.style.border =
                    "none";


                button.style.background =
                    "transparent";


                button.style.fontSize =
                    "24px";


                button.style.cursor =
                    "pointer";


                button.addEventListener(
                    "click",
                    function (event) {

                        event.preventDefault();

                        event.stopPropagation();


                        if (!chatInput) {
                            return;
                        }


                        chatInput.value +=
                            emoji;


                        chatInput.focus();
                    }
                );


                emojiGrid.appendChild(
                    button
                );
            }
        );
    }


    // =========================================================
    // OPEN / CLOSE EMOJI PICKER
    // =========================================================

    if (
        emojiBtn &&
        emojiPicker
    ) {

        emojiBtn.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                event.stopPropagation();


                emojiPicker.classList.toggle(
                    "show"
                );


                emojiPicker.classList.remove(
                    "d-none"
                );


                if (
                    emojiPicker.classList.contains(
                        "show"
                    )
                ) {

                    renderEmojis();
                }
            }
        );
    }


    // =========================================================
    // EMOJI SEARCH
    // =========================================================

    if (emojiSearch) {

        emojiSearch.addEventListener(
            "input",
            function () {

                renderEmojis();
            }
        );
    }


    // =========================================================
    // EMOJI TABS
    // =========================================================

    const emojiTabs =
        document.querySelectorAll(
            ".emoji-tab"
        );


    emojiTabs.forEach(
        function (tab) {

            tab.addEventListener(
                "click",
                function () {

                    emojiTabs.forEach(
                        function (item) {

                            item.classList.remove(
                                "active"
                            );
                        }
                    );


                    tab.classList.add(
                        "active"
                    );


                    renderEmojis();
                }
            );
        }
    );


    // =========================================================
    // CLOSE EMOJI PICKER OUTSIDE
    // =========================================================

    document.addEventListener(
        "click",
        function (event) {

            if (
                emojiPicker &&
                emojiBtn &&
                !emojiPicker.contains(
                    event.target
                ) &&
                !emojiBtn.contains(
                    event.target
                )
            ) {

                emojiPicker.classList.remove(
                    "show"
                );
            }
        }
    );


    // =========================================================
    // VOICE RECORDING
    // =========================================================

    let mediaRecorder = null;

    let audioChunks = [];

    let isRecording = false;


    if (voiceBtn) {

        voiceBtn.addEventListener(
            "click",
            async function (event) {

                event.preventDefault();


                // -------------------------------------------------
                // Do not record while editing
                // -------------------------------------------------

                if (editingMessageId) {

                    console.log(
                        "🚫 Voice recording disabled while editing."
                    );

                    return;
                }


                // -------------------------------------------------
                // STOP RECORDING
                // -------------------------------------------------

                if (isRecording) {

                    if (mediaRecorder) {

                        mediaRecorder.stop();
                    }

                    return;
                }


                // -------------------------------------------------
                // START RECORDING
                // -------------------------------------------------

                try {

                    const stream =
                        await navigator.mediaDevices
                            .getUserMedia({
                                audio: true
                            });


                    mediaRecorder =
                        new MediaRecorder(
                            stream
                        );


                    audioChunks = [];

                    isRecording = true;


                    voiceBtn.classList.add(
                        "recording"
                    );


                    mediaRecorder.ondataavailable =
                        function (event) {

                            if (
                                event.data &&
                                event.data.size > 0
                            ) {

                                audioChunks.push(
                                    event.data
                                );
                            }
                        };


                    mediaRecorder.onstop =
                        function () {

                            isRecording =
                                false;


                            voiceBtn.classList.remove(
                                "recording"
                            );


                            stream
                                .getTracks()
                                .forEach(
                                    function (track) {

                                        track.stop();
                                    }
                                );


                            const audioBlob =
                                new Blob(
                                    audioChunks,
                                    {
                                        type:
                                            "audio/webm"
                                    }
                                );


                            const reader =
                                new FileReader();


                            reader.onloadend =
                                function () {

                                    console.log(
                                        "🎙 Sending voice message..."
                                    );


                                    const payload = {

                                        receiver_id:
                                            receiverId,

                                        audio:
                                            reader.result
                                    };


                                    if (replyToId) {

                                        payload.reply_to_id =
                                            replyToId;
                                    }


                                    socket.emit(
                                        "send_voice",
                                        payload
                                    );


                                    clearReply();
                                };


                            reader.readAsDataURL(
                                audioBlob
                            );
                        };


                    mediaRecorder.start();


                    console.log(
                        "🎙 Voice recording started"
                    );


                } catch (error) {

                    console.error(
                        "❌ Microphone error:",
                        error
                    );


                    alert(
                        "Microphone permission is required for voice messages."
                    );
                }
            }
        );
    }


    // =========================================================
    // WEBRTC AUDIO CALL
    // =========================================================

    let peerConnection = null;

    let localStream = null;


    const rtcConfiguration = {
        iceServers: [
            {
                urls:
                    "stun:stun.l.google.com:19302"
            }
        ]
    };


    // =========================================================
    // CREATE PEER CONNECTION
    // =========================================================

    function createPeerConnection(
        targetUserId
    ) {

        peerConnection =
            new RTCPeerConnection(
                rtcConfiguration
            );


        peerConnection.onicecandidate =
            function (event) {

                if (
                    event.candidate
                ) {

                    socket.emit(
                        "ice_candidate",
                        {
                            target:
                                targetUserId,

                            candidate:
                                event.candidate
                        }
                    );
                }
            };


        peerConnection.ontrack =
            function (event) {

                if (
                    remoteAudio &&
                    event.streams &&
                    event.streams[0]
                ) {

                    remoteAudio.srcObject =
                        event.streams[0];

                    remoteAudio.play()
                        .catch(
                            function () {}
                        );
                }
            };


        return peerConnection;
    }


    // =========================================================
    // START AUDIO CALL
    // =========================================================

    async function startCall() {

        if (!receiverId) {
            return;
        }


        try {

            localStream =
                await navigator.mediaDevices
                    .getUserMedia({
                        audio: true,
                        video: false
                    });


            createPeerConnection(
                receiverId
            );


            localStream
                .getTracks()
                .forEach(
                    function (track) {

                        peerConnection.addTrack(
                            track,
                            localStream
                        );
                    }
                );


            const offer =
                await peerConnection
                    .createOffer();


            await peerConnection
                .setLocalDescription(
                    offer
                );


            socket.emit(
                "call_user",
                {
                    target:
                        receiverId,

                    offer:
                        offer
                }
            );


            if (callStatus) {

                callStatus.style.display =
                    "block";

                callStatus.textContent =
                    "Calling...";
            }


            if (callBtn) {
                callBtn.classList.add("d-none");
            }


            if (endCallBtn) {
                endCallBtn.classList.remove("d-none");
            }


            if (ringback) {

                ringback.play()
                    .catch(
                        function () {}
                    );
            }


            console.log(
                "📞 Calling user:",
                receiverId
            );


        } catch (error) {

            console.error(
                "❌ Call error:",
                error
            );


            if (callStatus) {

                callStatus.style.display =
                    "block";

                callStatus.textContent =
                    "Call failed";
            }
        }
    }


    // =========================================================
    // CALL BUTTON
    // =========================================================

    if (callBtn) {

        callBtn.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                startCall();
            }
        );
    }


    // =========================================================
    // INCOMING CALL
    // =========================================================

    let incomingCallerId =
        null;

    let incomingOffer =
        null;


    socket.on(
        "incoming_call",
        function (data) {

            console.log(
                "📞 Incoming call:",
                data
            );


            incomingCallerId =
                Number(data.from);


            incomingOffer =
                data.offer;


            if (incomingCall) {

                incomingCall.classList.remove(
                    "d-none"
                );
            }


            if (ringtone) {

                ringtone.currentTime =
                    0;

                ringtone.play()
                    .catch(
                        function () {}
                    );
            }
        }
    );


    // =========================================================
    // ACCEPT CALL
    // =========================================================

    if (acceptCallBtn) {

        acceptCallBtn.addEventListener(
            "click",
            async function () {

                try {

                    if (ringtone) {

                        ringtone.pause();

                        ringtone.currentTime =
                            0;
                    }


                    if (incomingCall) {

                        incomingCall.classList.add(
                            "d-none"
                        );
                    }


                    localStream =
                        await navigator.mediaDevices
                            .getUserMedia({
                                audio: true,
                                video: false
                            });


                    createPeerConnection(
                        incomingCallerId
                    );


                    localStream
                        .getTracks()
                        .forEach(
                            function (track) {

                                peerConnection.addTrack(
                                    track,
                                    localStream
                                );
                            }
                        );


                    await peerConnection
                        .setRemoteDescription(
                            new RTCSessionDescription(
                                incomingOffer
                            )
                        );


                    const answer =
                        await peerConnection
                            .createAnswer();


                    await peerConnection
                        .setLocalDescription(
                            answer
                        );


                    socket.emit(
                        "call_accepted",
                        {
                            target:
                                incomingCallerId,

                            answer:
                                answer
                        }
                    );


                    if (callStatus) {

                        callStatus.style.display =
                            "block";

                        callStatus.textContent =
                            "Connected";
                    }


                    if (callBtn) {
                        callBtn.classList.add("d-none");
                    }


                    if (endCallBtn) {
                        endCallBtn.classList.remove("d-none");
                    }


                } catch (error) {

                    console.error(
                        "❌ Accept call error:",
                        error
                    );
                }
            }
        );
    }


    // =========================================================
    // REJECT CALL
    // =========================================================

    if (rejectCallBtn) {

        rejectCallBtn.addEventListener(
            "click",
            function () {

                if (ringtone) {

                    ringtone.pause();

                    ringtone.currentTime =
                        0;
                }


                if (incomingCall) {

                    incomingCall.classList.add(
                        "d-none"
                    );
                }


                incomingCallerId =
                    null;

                incomingOffer =
                    null;
            }
        );
    }


    // =========================================================
    // CALL ACCEPTED
    // =========================================================

    socket.on(
        "call_accepted",
        async function (data) {

            console.log(
                "📞 Call accepted"
            );


            try {

                if (!peerConnection) {
                    return;
                }


                await peerConnection
                    .setRemoteDescription(
                        new RTCSessionDescription(
                            data.answer
                        )
                    );


                if (ringback) {

                    ringback.pause();

                    ringback.currentTime =
                        0;
                }


                if (callStatus) {

                    callStatus.style.display =
                        "block";

                    callStatus.textContent =
                        "Connected";
                }


            } catch (error) {

                console.error(
                    "❌ Call accepted error:",
                    error
                );
            }
        }
    );


    // =========================================================
    // ICE CANDIDATE
    // =========================================================

    socket.on(
        "ice_candidate",
        async function (data) {

            if (
                !peerConnection ||
                !data.candidate
            ) {

                return;
            }


            try {

                await peerConnection
                    .addIceCandidate(
                        new RTCIceCandidate(
                            data.candidate
                        )
                    );


            } catch (error) {

                console.error(
                    "❌ ICE candidate error:",
                    error
                );
            }
        }
    );


    // =========================================================
    // END CALL
    // =========================================================

    function endCall() {

        if (ringtone) {

            ringtone.pause();

            ringtone.currentTime =
                0;
        }


        if (ringback) {

            ringback.pause();

            ringback.currentTime =
                0;
        }


        if (localStream) {

            localStream
                .getTracks()
                .forEach(
                    function (track) {

                        track.stop();
                    }
                );

            localStream = null;
        }


        if (peerConnection) {

            peerConnection.close();

            peerConnection =
                null;
        }


        if (remoteAudio) {

            remoteAudio.srcObject =
                null;
        }


        if (callStatus) {

            callStatus.textContent =
                "";

            callStatus.style.display =
                "none";
        }


        if (callBtn) {
            callBtn.classList.remove("d-none");
        }


        if (endCallBtn) {
            endCallBtn.classList.add("d-none");
        }


        if (incomingCall) {

            incomingCall.classList.add(
                "d-none"
            );
        }
    }


    if (endCallBtn) {

        endCallBtn.addEventListener(
            "click",
            function () {

                socket.emit(
                    "end_call",
                    {
                        target:
                            receiverId
                    }
                );


                endCall();
            }
        );
    }


    // =========================================================
    // REMOTE CALL ENDED
    // =========================================================

    socket.on(
        "call_ended",
        function () {

            console.log(
                "📞 Call ended by other user"
            );

            endCall();
        }
    );


    // =========================================================
    // ESCAPE KEY
    // =========================================================

    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Escape" &&
                editingMessageId
            ) {

                cancelEditing();

                return;
            }


            if (
                event.key === "Escape"
            ) {

                closeAllMessageMenus();

                if (emojiPicker) {

                    emojiPicker.classList.remove(
                        "show"
                    );
                }
            }
        }
    );


    // =========================================================
    // ENTER KEY WHILE EDITING
    // =========================================================

    if (chatInput) {

        chatInput.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Enter" &&
                    !event.shiftKey &&
                    editingMessageId
                ) {

                    event.preventDefault();

                    saveEditedMessage();
                }
            }
        );
    }


    // =========================================================
    // INITIALIZE EVERYTHING
    // =========================================================

    setTimeout(
        function () {

            initializeExistingReplyButtons();

            initializeExistingMessageMenus();

            scrollChatToBottom();

        },
        100
    );


    // =========================================================
    // FINAL STATUS
    // =========================================================

    console.log(
        "🚀 Nextura chat.js initialized successfully."
    );

})();