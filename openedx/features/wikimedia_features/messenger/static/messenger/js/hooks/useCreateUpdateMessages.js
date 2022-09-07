import { useEffect } from 'react';
import { toast } from 'react-toastify';

import useClient from "./useClient";


export default function useCreateUpdateMessages(
    inboxList, setInboxList, selectedInboxUser, setSelectedInboxMessages, context) {
    const { client, notification } = useClient();
    let currentInbox = {};

    const createMessage = async(message, setMessage, updateLastMessage, setReplying) => {
        try {
            const createdMessage = (await client.post(context.MESSAGE_URL, {
                receiver: selectedInboxUser,
                message: message
            })).data;
            if (createdMessage) {
                setSelectedInboxMessages((prevMsgs) => [createdMessage, ...prevMsgs]);
                setMessage("");
                setReplying(false);
                updateLastMessage(message);
            }
            notification(toast.success, context.META_DATA.success.send_message);
        } catch (e) {
            notification(toast.error, context.META_DATA.error.send_message);
            console.error(e);
        }
    }

    const createGroupMessages = async(message, setMessage, users) => {
        try {
            const UpdatedInbox = (await client.post(context.BULK_MESSAGE_URL, {
                receivers: users.map((user) => user.id),
                message: message
            })).data;

            updateInboxList(UpdatedInbox);
            updateOpenedConversation(message, users);
            setMessage("");
            notification(toast.success, context.META_DATA.success.send_messages);
        } catch (e) {
            notification(toast.error, context.META_DATA.error.send_messages);
            console.error(e);
        }
    }

    const updateInboxList = (UpdatedInbox ) => {
        let UpdatedInboxIds = UpdatedInbox.map(inbox => inbox.id)
        let newList = inboxList.filter((inbox) => !UpdatedInboxIds.includes(inbox.id))
        newList = [...UpdatedInbox, ...newList];
        setInboxList(newList);
    }

    const updateOpenedConversation = (message, users) => {
        let isConversationOpened = users.some((user) => user.username == selectedInboxUser);
        if (isConversationOpened) {
            setSelectedInboxMessages((prevMsgs) => {
                return [{
                    sender: context.LOGIN_USER,
                    sender_img: context.LOGIN_USER_IMG,
                    created: "now",
                    message
                }, ...prevMsgs, ];
            });
        }
    }

    const updateUnreadCount = async(inboxId) => {
        try {
            let updatedInbox = (await client.patch(`${context.INBOX_URL}${inboxId}/`, {
                unread_count: 0
            })).data;
            if (updatedInbox) {
                setInboxList((previousList) => {
                    return previousList.map((inbox) => {
                        return (inbox.id === updatedInbox.id ? updatedInbox : inbox);
                    })
                });
            }
        } catch (ex) {
            notification(toast.error, context.META_DATA.error.read_messages);
            console.error(ex);
        }
    }

    const updateLastMessage = (message) => {
        currentInbox = inboxList.find((inbox) => inbox.with_user == selectedInboxUser);
        if (currentInbox) {
            currentInbox.last_message = message.length > 30 ? `${message.substring(0, 30)}...`: message;
            setInboxList((previousList) => {
                return previousList.map((inbox) => {
                    return (inbox.id === currentInbox.id ? currentInbox : inbox);
                });
            });
        }
    }

    useEffect(() => {
        currentInbox = inboxList.find((inbox) => inbox.with_user == selectedInboxUser);
        if (currentInbox && currentInbox.unread_count) {
            setTimeout(() => { updateUnreadCount(currentInbox.id) }, 3000);

        }
    }, [selectedInboxUser]);

    return { updateLastMessage, createGroupMessages, createMessage, updateUnreadCount };
}
