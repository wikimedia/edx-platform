import React from "react";
import ReactDOM from "react-dom";
import TranslationContent from "./TranslationContent";

import '../../scss/main.scss';

export class Translations {
  constructor(context) {
    ReactDOM.render(<TranslationContent context={context} />, document.getElementById("root"));
  }
}
