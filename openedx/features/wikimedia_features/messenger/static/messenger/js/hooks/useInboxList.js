import { useState, useEffect } from 'react';
import useClient from "./useClient";

import { toast } from 'react-toastify';

export default function useInboxList(inboxPageNumber, setSelectedInboxUser, context, setInboxPageNumber, searchInbox) {
    const { client, notification } = useClient();
    const [inboxList, setInboxList] = useState([]);
    const [inboxHasMore, setInboxHasMore] = useState(false);
    const [inboxLoading, setInboxLoading] = useState(false);

    const fetchInboxList = async(pageNumber) => {
        try {
            setInboxLoading(true);
            const inboxListData = (await client.get(`${context.INBOX_URL}?page=${pageNumber}&search=${searchInbox}`)).data;
            if (inboxListData) {
                if (pageNumber == 1) {
                    setInboxList(inboxListData.results);
                    if (inboxListData.results.length) setSelectedInboxUser(inboxListData.results[0].with_user);
                } else {
                    setInboxList((previousList) => [...previousList, ...inboxListData.results]);
                }
                setInboxHasMore(pageNumber < inboxListData.num_pages);

            }
            setInboxLoading(false);
        } catch (e) {
            notification(toast.error, context.META_DATA.error.load_conversation);
            console.error(e);
        }
    }

    useEffect(() => {
        setInboxLoading(true);
        const delayDebounceFetch= setTimeout(() => {
            setInboxPageNumber(1);
            fetchInboxList(1);
          }, 3000)
          return () => clearTimeout(delayDebounceFetch)
    }, [searchInbox]);

    useEffect(() => {
        if (inboxPageNumber > 1) fetchInboxList(inboxPageNumber)
    }, [inboxPageNumber]);

    return { inboxList, setInboxList, inboxLoading, inboxHasMore };
}
