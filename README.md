# New_JeBiF

## Introduction
The goal of this repo is to create the structure of the JeBiF website, previously made with WordPress.
Depending on external circumstances, the others aspects of the website related to the elections will be added.

## Dependencies
`python -m pip install Django` for Django, the Python framework used to make this website (Python 3 is required).

For Bootstrap 5, check the official website: https://getbootstrap.com/docs/5.0/getting-started/download/. It is used to handle code for html pages.

`pip install django-tinymce` for tinymce, used for writing the article in the admin page.

`pip install django-crispy-forms` for cripsy-forms, used to have nicer forms.

## Structure
This website is made with 7 categories in mind (L'association,  Evènements, Bioinformatique, Vulgarisation, Liens utiles, Nous rejoindre, and Contact). Each category has differents sub-categories. In addition, there is also a home page (Accueil).

Article is a class made to write articles, one for each category and subcategory (but it is designed to be able to present more). Only the home page (Accueil) has more articles, which could be considered "News".

Each page (Accueil, Category and SubCategory) present a Navigation bar (nav.html) to navigate in the website, and a side bar (side.html) to present different informations (next events, social medias, useful link, irc, recent articles, RSS and the Licence). Under the navbar is the banner of the website.

## Users
In order to add more info to the users, a new class was created, UserInfo. It is accessible by doing user.info when you are using a User.
The cron part is a replicate in Python3 of the cron part in the old repositories. It may need more adjustements.

Each User can have access to its infos from the website, using buttons from the navbar when they are logged in. 
In case they aren't logged in, a login button and a Registration button are displayed. Else, it's a Profile button and a Logout Button. 
The admin(s) have its Profile Button replaced by an Admin Button, with a page  showing links to their own profile or various Admin functions (like validating Membership of Users).

## Elections
There is an Election class with a name (label) and a description (more fields too, but may change), which can be opened or closed. For each Election there can be Candidates, a class linked to an Election and with a label and a description. In order for the Users to vote, a Vote class was created: it represent the vote of the user, and is linked to an Election and a Candidate. To populate the list of voters, a has_voted parameter was added which will be changed to True when the user vote, which helps showing only the candidates remaining in an election without a vote from the user. The List of the Opened Election is accessible trough a button in the Navbar. Only the Opened Election will be visible (with a link). On the Election page, only the candidates for which the user hasn't voted yet will appear; in case there is none, a new page will inform the user.

## Miscellaneous
Made by Alexandre Lerévérend: ask for any question.

### TODO:
-cron in users is not correct yet, some unknown files are called (need to change links)

-navbar isn't aesthetic yet

-remove unwanted old code (currently commented) when sure it's not needed

-check if emails are sent correctly ( maybe some changes in settings for that too, plus all the methods and functions in users)

-add a page with a form to create an election (or not if admin interface is enough)

-add a page with a form to create an event (for everyuser? if yes, limit to only one pending event)