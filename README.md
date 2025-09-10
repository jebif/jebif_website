# New_JeBiF

## Introduction
The goal of this repo is to create the structure of the JeBiF website, previously made with WordPress.
Depending on external circumstances, the others aspects of the website related to the elections will be added.

## Dependencies
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

## Miscellaneous
Made by Alexandre Lerévérend: ask for any question.

### TODO:
-cron in users is not correct yet, some unknown files are called (need to change links)

-navbar isn't aesthetic yet

-remove unwanted old code (currently commented) when sure it's not needed

-check if emails are sent correctly ( maybe some changes in settings for that too, plus all the methods and functions in users)