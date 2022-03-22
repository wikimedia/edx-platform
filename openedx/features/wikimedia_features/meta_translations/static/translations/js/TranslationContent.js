import React, { useState } from 'react';

const TranslationContent = ({context}) => {
    const [sections, setSections] = useState([]);
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        setIsLoading(true);
        setProducts([]);
        const fetchData = async () => {
          const jsonData = await fetchSections(catalogId, page);
          setProducts(jsonData.results);
          setCount(jsonData.count);
          setIsLoading(false);
        };
        fetchData();
      }, [page, catalogId, triggerDelete]);
  
    return (
      <>
        {isUserFetching && <CircularProgress />}
        {!isUserFetching && (
          <Layout>
            <Routes />
            <Toaster position='top-right' reverseOrder={false} />
          </Layout>
        )}
      </>
    );
  };
  
  export default App;