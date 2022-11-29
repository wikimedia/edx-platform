import React, { useEffect, useState } from "react";

function TranslationBlock({ id, title, content, blockType, isTranslated, isParsed, redirectUrl }) {
  const [isExpended, setIsExpended] = useState(false);

  const onExpended = () => {
    setIsExpended(!isExpended);
  }

  const getContentBlock = () => {
    if (content) {
      if (isParsed) {
        return (
          <ul>
            {Object.entries(content).map(item => <li key={item[0]}>{item[1] ? item[1] : '--'}</li>)}
          </ul>
        )
      }
      else if (blockType == 'html') {
        return (
          <pre>{content}</pre>
        )
      }
    }
    return (content);
  }

  return (
    <div id={id} className="translation-block">
      <div className="header">
        <div className="header-title">
          <span className="title">{title}</span>
          {
            content && <div className="title-buttons">
              {isExpended && <span className="btn fa fa-chevron-down" onClick={onExpended}></span>}
              {!isExpended && <span className="btn fa fa-chevron-right" onClick={onExpended}></span>}
            </div>
          }
        </div>
        <div className="actions">
          {
            redirectUrl != '' && (
              <a className="btn" href={redirectUrl} title='wiki translation' target="_blank">
                <i className="fa fa-external-link"></i>
              </a>
            )
          }
        </div>
      </div>
      {
        content && !isExpended && <div className="content" style={{ maxHeight: '3em' }}>
          {getContentBlock()}
        </div>
      }
      {
        content && isExpended && <div className="content" style={{ maxHeight: 'max-content' }}>
          {getContentBlock()}
        </div>
      }
    </div>
  )
}

export default TranslationBlock;
