# Development Branching Strategy

We follow this branching model to streamline development and deployment:

| Branch             | Description                                                      |
|--------------------|------------------------------------------------------------------|
| `master`           | Mirrors the upstream `master`; used to track and verify changes. |
| `develop`          | Primary development branch; deployed to development, staging and then production environments.    |
| `<feature-branch>` | Used for new features or bug fixes; merged into `develop`.       |

# Wikimedia specific customizations

## edx-platform customizations

Almost all custom code for wikimedia can be found in [wikimedia_features](https://github.com/wikimedia/edx-platform/tree/develop/openedx/features/wikimedia_features) directory.

For a more specific outlook, the following table shows what each app in this directory is for.

| App                | Description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `admin_dashboard`  | Customizations related to the admin dashboard                               |
| `email`            | Handles sending emails for various events                                   |
| `messenger`        | Our custom-built messaging application                                      |
| `meta_translations`| Custom translations system integration used by Wikimedia                   |
| `progress_tab`     | Custom course progress tab                                                  |
| `auth_backend`     | Custom authentication mechanism using Wikimedia's authentication server     |
| `wikimedia_general`| Miscellaneous features not covered by the above categories                  |

All new code, unless absolute necessary, should be added inside this directory to provide an easy outlook on the customizations made from the base branch and for ease of upgradibility to new releases of Open edX.

## Theme

We use a custom theme that follows the wikimedia logo and colours. The theme utilized for wikilearn is available here: https://github.com/wikimedia/wikilearn-edx-theme/tree/develop

The branching model we follow for the theme to streamline development and deployment is as follows:

| Branch             | Description                                                      |
|--------------------|------------------------------------------------------------------|
| `develop`          | Primary development branch; deployed to development, staging and then production environments.    |
| `<feature-branch>` | Used for new features or bug fixes; merged into `develop`.       |

# Deployment Scheme

We follow a three phase deployment strategy.

First, we deploy the develop branch to the Development Environment. Then, deploy to the staging environment which is a mirror of the production environment.

Once everything is tested, we deploy to the production environment.

The servers are available live on the following urls:

| Environment   | LMS URL             | Studio URL              |
|---------------|---------------------|--------------------------|
| Development   | https://dev.learn.wiki/    | https://studio.dev.learn.wiki/ |
| Staging       | https://stage.learn.wiki/   | https://studio.stage.learn.wiki/ |
| Production    | https://learn.wiki/    | https://studio.learn.wiki/ |

> **_NOTE:_**  Development and Staging environments are protected behind credentials which have been shared with the relevant members.


# Translations Management

On the first day of each month, translations that were added to the [wm/localization](https://github.com/wikimedia/edx-platform/tree/wm/localization)  branch are verified and merged into the develop branch. These translations are then deployed onto the development environment whenever a new release is created. Once the translations are verified, these changes are depoyed onto the staging environment and finally to the production environment.
