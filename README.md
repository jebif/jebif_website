# New_JeBiF

## Introduction
The goal of this repo is to create the structure of the JeBiF website, previously made with WordPress.
Depending on external circumstances, the others aspects of the website related to the elections will be added.

## Installation
Python 3.12+ is required.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp jebif_main/.env.example jebif_main/.env   # then edit the values
python manage.py migrate
python manage.py populate_category
python manage.py populate_sidebar
python manage.py runserver
```

## Configuration
All settings that change between environments are read from `jebif_main/.env` (never commit it).
See `jebif_main/.env.example` for the full list. The most important ones:

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | *(required)* | Long random string |
| `DEBUG` | `False` | `True` only in development (mails are then printed in the console) |
| `COOKIE_SECURE` | `True` | Set `False` for local development over plain HTTP |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | jebif.fr, beta.jebif.fr | Comma-separated lists |
| `HTTP_DOMAIN` | `https://jebif.fr` | Domain used in links sent by e-mail |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_FROM` | | SMTP configuration |
| `CONTACT_EMAIL` | `contact@jebif.fr` | Mailbox receiving the contact form messages |
| `ADMINS` | *(empty)* | Comma-separated e-mails receiving the server errors |
| `SHOW_DEV_BANNER` | `False` | Show the "development website" banner (beta.jebif.fr) |
| `BEHIND_HTTPS_PROXY`, `TRUST_X_FORWARDED_FOR` | `False` | Set `True` behind nginx (if nginx sets these headers) |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `False`, `0` | HTTPS hardening, enable in production |
| `SERVE_MEDIA` | `True` | Set `False` once nginx serves `/media/` |
| `STATIC_DIR`, `CACHE_DIR`, `LOG_FILE`, `SQLITE_PATH` | inside the project | Paths |

A Content Security Policy is sent in *report-only* mode (`SECURE_CSP_REPORT_ONLY` in the settings):
check the browser console for violations, then rename it to `SECURE_CSP` to enforce it.

## Production
- `python manage.py collectstatic`, serve `STATIC_DIR` (`/staticfiles/`) and `media/` (`/media/`) with nginx.
- Run with gunicorn behind nginx.
- Daily cron job (membership expiration and reminder mails):
  `0 6 * * * cd /path/to/jebif_website && venv/bin/python manage.py expire_memberships`
  (`--dry-run` shows what would be done).

## Tests
```bash
SECRET_KEY=test COOKIE_SECURE=False python manage.py test
```
They also run on GitHub Actions for each push (`.github/workflows/tests.yml`).

## Structure
This website is made with 7 categories in mind (L'association,  Evènements, Bioinformatique, Vulgarisation, Liens utiles, Nous rejoindre, and Contact). Each category has differents sub-categories. In addition, there is also a home page (Accueil).

Article is a class made to write articles, one for each category and subcategory (but it is designed to be able to present more). Only the home page (Accueil) has more articles, which could be considered "News". There is three cases:
* No Category: Articles will be present in the "Accueil" page.
* Category (only): Article will be present when you check the Category page.
* Category with Subcategory: Article will be present when you check the related Subcategory of a Category. When you create such article, make sure you choose a SubCategory belong to the Category you have chosen (else there will be an error).

Each page (Accueil, Category and SubCategory) present a Navigation bar (nav.html) to navigate in the website, and a side bar (side.html) to present different informations (next events, social medias, useful link, irc, recent articles, RSS and the Licence). Under the navbar is the banner of the website.

## Users
In order to add more info to the users, a new class was created, UserInfo. It is accessible by doing user.info when you are using a User.
After registration, the user receives a link (valid 24 hours, single use) to verify their e-mail address and complete their information. A membership request is only possible with a verified address and lasts one year.

Each User can have access to its infos from the website, using buttons from the navbar when they are logged in. 
In case they aren't logged in, a login button and a Registration button are displayed. Else, it's a Profile button and a Logout Button. 
The admin(s) have its Profile Button replaced by an Admin Button, with a page  showing links to their own profile or various Admin functions (like validating Membership of Users).

## Elections
There is an Election class with a name (label) and a description (more fields too, but may change), which can be opened or closed. For each Election there can be Candidates, a class linked to an Election and with a label and a description. In order for the Users to vote, a Vote class was created: it represent the vote of the user, and is linked to an Election and a Candidate. To populate the list of voters, a has_voted parameter was added which will be changed to True when the user vote, which helps showing only the candidates remaining in an election without a vote from the user. The List of the Opened Election is accessible trough a button in the Navbar. Only the Opened Election will be visible (with a link). On the Election page, only the candidates for which the user hasn't voted yet will appear; in case there is none, a new page will inform the user.

## Miscellaneous
After the creation of the database, you can create automatically the default categories and subcategories with:
`python manage.py populate_category`
In case previous categories were made, it will compare the slugs to create or not the categories (and sub).

Made by Alexandre Lerévérend: ask for any question.

-develop more the admin interface for pendingEvents (name, etc)

-Finish the documentation if needed (only models done)
