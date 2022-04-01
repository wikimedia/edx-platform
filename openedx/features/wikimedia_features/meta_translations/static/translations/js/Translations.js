import React from "react";
import ReactDOM from "react-dom";
import TranslationContent from "./TranslationContent";

export class Translations {
    constructor(context) {
        console.log(context);
        ReactDOM.render(<TranslationContent context={context} />, document.getElementById("root"));
    }
}
