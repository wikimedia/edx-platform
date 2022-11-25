import React from "react";
import { BrowserRouter, Switch, Route } from "react-router-dom";
import CourseTranslations from "./components/CourseTranslations";
import DiscoverCoursesContent from "./components/DiscoverCoursesContent";

export default function Navigator({ context }) {
  return (
    <BrowserRouter>
      <Switch>
        <Route exact path="/meta_translations/discover_courses/">
          <DiscoverCoursesContent context={context} />
        </Route>
        <Route exact path="/meta_translations/discover_courses/:course_id">
          <CourseTranslations context={context} />
        </Route>
      </Switch>
    </BrowserRouter>
  );
}
