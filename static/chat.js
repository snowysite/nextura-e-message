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
    // APPEND MESSAGE TO CHAT
    // =========================================================

    function appendMessage(data) {

        if (!chatBox) {
            return;
        }


        const messageSenderId =
            Number(data.sender_id);

        const isMine =
            messageSenderId === senderId;


        const wrapper =
            document.createElement("div");


        wrapper.className =
            isMine
                ? "d-flex justify-content-end mb-2"
                : "d-flex justify-content-start mb-2";


        const bubble =
            document.createElement("div");


        bubble.className =
            isMine
                ? "nextura-message sent"
                : "nextura-message received";


        bubble.style.maxWidth =
            "75%";

        bubble.style.padding =
            "10px 14px";

        bubble.style.borderRadius =
            "15px";

        bubble.style.wordBreak =
            "break-word";


        // =====================================================
        // VOICE MESSAGE
        // =====================================================

        if (
            data.message_type === "voice" ||
            data.audio
        ) {

            const audio =
                document.createElement("audio");

            audio.controls = true;

            audio.preload = "metadata";

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


            bubble.appendChild(audio);

        }

        // =====================================================
        // TEXT MESSAGE
        // =====================================================

        else {

            const text =
                document.createElement("span");

            text.textContent =
                data.message || "";

            bubble.appendChild(text);
        }


        // =====================================================
        // MESSAGE STATUS
        // =====================================================

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

            bubble.appendChild(status);
        }


        wrapper.appendChild(bubble);

        chatBox.appendChild(wrapper);

        scrollChatToBottom();
    }


    // =========================================================
    // SEND TEXT MESSAGE
    // =========================================================

    if (chatForm) {

        chatForm.addEventListener(
            "submit",
            function (event) {

                // VERY IMPORTANT:
                // Prevent the browser from submitting
                // the form normally and reloading the page.

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


                if (!socket) {

                    console.error(
                        "❌ Socket.IO is unavailable."
                    );

                    return;
                }


                console.log(
                    "📤 Sending message:",
                    message
                );


                // =================================================
                // SEND TO FLASK SOCKET.IO
                // =================================================

                socket.emit(
                    "send_message",
                    {
                        receiver_id:
                            receiverId,

                        message:
                            message
                    }
                );


                // Clear input immediately.

                chatInput.value = "";

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


            // Make sure the message belongs
            // to the conversation currently open.

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
        "❤️‍🔥",
        "🤣"
    ];


    // =========================================================
    // RENDER EMOJIS
    // =========================================================

    function renderEmojis() {

        if (!emojiGrid) {
            return;
        }


        emojiGrid.innerHTML = "";


        emojis.forEach(
            function (emoji) {

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
                    function () {

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

                emojiPicker.classList.toggle(
                    "d-none"
                );


                if (
                    !emojiPicker.classList.contains(
                        "d-none"
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

                // Emoji characters themselves don't have
                // meaningful text search, but keeping the
                // input functional prevents errors.

                renderEmojis();
            }
        );
    }


    // =========================================================
    // CLOSE EMOJI PICKER WHEN CLICKING OUTSIDE
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

                emojiPicker.classList.add(
                    "d-none"
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


                // ---------------------------------------------
                // STOP RECORDING
                // ---------------------------------------------

                if (isRecording) {

                    if (mediaRecorder) {

                        mediaRecorder.stop();
                    }

                    return;
                }


                // ---------------------------------------------
                // START RECORDING
                // ---------------------------------------------

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


                                    socket.emit(
                                        "send_voice",
                                        {
                                            receiver_id:
                                                receiverId,

                                            audio:
                                                reader.result
                                        }
                                    );
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

                callStatus.textContent =
                    "Calling...";
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

                        callStatus.textContent =
                            "Connected";
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


        if (callStatus) {

            callStatus.textContent =
                "";
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
    // INITIAL SCROLL
    // =========================================================

    setTimeout(
        function () {

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
