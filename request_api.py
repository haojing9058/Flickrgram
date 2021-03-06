"""For requesting data from Flickr API"""

import requests
import json
from pprint import pprint
import os
import datetime
import reverse_geocoder as rg
from model import User, Photo
from model import connect_to_db, db
import db_utils


API_KEY = os.environ['API_KEY']
API_URL = "https://api.flickr.com/services/rest"
RESPONSE_FORMAT = 'json&nojsoncallback=1'


def base_params():
    """Helper function to get based parameters."""
    return {
            'api_key': API_KEY,
            'format': 'json',
            'nojsoncallback': '1',
        }


def get_userid_by_username(username):
    """Get a user's user_id given a username"""

    if db.session.query(User).filter(User.username == username).first() is None:
        params_find_by_username = base_params()
        params_find_by_username['method'] = "flickr.people.findByUsername"
        params_find_by_username['username'] = username
        response_username = requests.get(API_URL, params=params_find_by_username).json()
        if response_username['stat'].encode('utf-8') == 'fail':
            return response_username['stat']
        else:
            user_id = response_username['user']['nsid'].encode('utf-8')
            user = User(user_id=user_id, username=username)
            db_utils.create_user(user)

    else:
        user = db.session.query(User).filter(User.username == username).one()

    return user


def seed_photos_by_userid(user_id, sort='interesting', per_page=100):
    """
    Seed a user's photos into database given a user_id.
    sort: faves, views, comments or interesting.
    per_page: The maximum value is 500.
    """
    params = base_params()
    params['method'] = "flickr.photos.getPopular"
    params['user_id'] = user_id
    params['sort'] = 'interesting'
    params['extras'] =','.join(['description','date_taken', 'owner_name', 'geo', 
        'tags', 'url_q'])
    params['per_page'] = per_page
    response = requests.get(API_URL, params=params).json()
    photos = response['photos']['photo']

    for p in photos:
        photo_id = p['id'].encode('utf-8')

        if db.session.query(Photo).get(photo_id) is None:
            user_id = p['owner'].encode('utf-8')
            username = p['ownername'].encode('utf-8')
            description = p['description']['_content'].encode('utf-8')
            tags = p['tags'].encode('utf-8')
            title = p['title'].encode('utf-8')
            url = p['url_q'].encode('utf-8')
            date_taken = p['datetaken'].encode('utf-8')
            lat = p['latitude']
            lon = p['longitude']
            if lat == 0 and lon == 0:
                country_code = None
            else:
                country_code = rg.search((lat, lon))[0]['cc']

            photo = Photo(photo_id=photo_id, user_id=user_id, username=username,
            description=description, tags=tags, title=title, url=url, 
            date_taken=date_taken, lat=lat, lon=lon, country_code=country_code)

            db_utils.add_photo(photo)
        else:
            pass


def recommendation_by_text(tags, text, per_page=36):
    """
    Get the most relavent photos based on given text info(tags, title and description)
    tags: ata comma-delimited list of tags
    text: list of words
    Add the photos into db if it's not in it, and return a list of photo_id.
    """
    params = base_params()
    params['method'] = "flickr.photos.search"
    params['tags'] = tags
    params['tag_mode'] = 'any'
    params['text'] = []
    params['sort'] = 'interestingness-desc'
    params['content_type'] = 1
    params['media'] = 'photos'
    params['extras'] =','.join(['description','date_taken', 'owner_name', 'geo', 
        'tags', 'url_q'])
    params['per_page'] = per_page
    response = requests.get(API_URL, params=params).json()

    photos = response['photos']['photo'] #a list of photos

    photo_ids = []
    for p in photos:     
        photo_id = p['id'].encode('utf-8')
        photo_ids.append(photo_id)

        if db.session.query(Photo).get(photo_id) is None:
            user_id = p['owner'].encode('utf-8')
            username = p['ownername'].encode('utf-8')
            if db.session.query(User).get(user_id) is None:
                user = User(user_id=user_id, username=username)
                db_utils.create_user(user)
            description = p['description']['_content'].encode('utf-8')
            tags = p['tags'].encode('utf-8')
            title = p['title'].encode('utf-8')
            url = p['url_q'].encode('utf-8')
            date_taken = p['datetaken'].encode('utf-8')
            lat = p['latitude']
            lon = p['longitude']
            if lat == 0 and lon == 0:
                country_code = None
            else:
                country_code = rg.search((lat, lon))[0]['cc']

            photo = Photo(photo_id=photo_id, user_id=user_id, username=username,
            description=description, tags=tags, title=title, url=url, 
            date_taken=date_taken, lat=lat, lon=lon, country_code=country_code)

            db_utils.add_photo(photo)

        else:
            pass

    return photo_ids

def recommendation_by_geo(lat, lon, per_page=36):
    """
    Get most relavent photos based on given text info(tags, title and description)
    tags: a comma-delimited list of tags
    text: list of words
    Add the photos into db if it's not in it, and return a list of photo_id.
    """
    params = base_params()
    params['method'] = "flickr.photos.search"
    params['lat'] = lat
    params['lon'] = lon
    params['sort'] = 'interestingness-desc'
    params['content_type'] = 1
    params['accuracy'] = 3
    params['extras'] =','.join(['description','date_taken', 'owner_name', 'geo', 
        'tags', 'url_q'])
    params['per_page'] = per_page
    response = requests.get(API_URL, params=params).json()

    photos = response['photos']['photo'] #a list of photos

    photo_ids = []
    for p in photos:     
        photo_id = p['id'].encode('utf-8')
        photo_ids.append(photo_id)

        if db.session.query(Photo).get(photo_id) is None:
            user_id = p['owner'].encode('utf-8')
            username = p['ownername'].encode('utf-8')
            if db.session.query(User).get(user_id) is None:
                user = User(user_id=user_id, username=username)
                db_utils.create_user(user)
            description = p['description']['_content'].encode('utf-8')
            tags = p['tags'].encode('utf-8')
            title = p['title'].encode('utf-8')
            url = p['url_q'].encode('utf-8')
            date_taken = p['datetaken'].encode('utf-8')
            lat = p['latitude']
            lon = p['longitude']
            if lat == 0 and lon == 0:
                country_code = None
            else:
                country_code = rg.search((lat, lon))[0]['cc']

            photo = Photo(photo_id=photo_id, user_id=user_id, username=username,
            description=description, tags=tags, title=title, url=url, 
            date_taken=date_taken, lat=lat, lon=lon, country_code=country_code)

            db_utils.add_photo(photo)

        else:
            pass

    return photo_ids


def user_pool(group_id):
    # get group_id using https://www.flickr.com/services/api/explore/flickr.urls.lookupGroup
    """Get Flickr user members of the given Flickr group"""
    params = base_params()
    params['method'] = "flickr.groups.members.getList"
    params['group_id'] = group_id
    params['per_page'] = 100

    response = requests.get(API_URL, params=params).json()

    return response 


if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)

    connect_to_db(app)