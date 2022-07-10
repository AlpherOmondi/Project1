#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import sys
import dateutil.parser
import babel
from flask import (
    Flask,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    jsonify)
import phonenumbers
from datetime import datetime
import logging
from logging import Formatter, FileHandler
from wtforms import ValidationError
from forms import *
from models import *

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

# used for formatting user time input


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime

# validates user phone numbers


def phone_validator(num):
    parsed = phonenumbers.parse(num, "US")
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError('Must be a valid US phone number.')

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

# home page route handler
@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

# venues page route handler
@app.route('/venues')
def venues():
    # list for storing venue data
    data = []

    # get all the venues and create a set from the cities
    venues = Venue.query.all()
    venue_cities = set()
    for venue in venues:
        # add city/state tuples
        venue_cities.add((venue.city, venue.state))

    # for each unique city/state, add venues
    for location in venue_cities:
        data.append({
            "city": location[0],
            "state": location[1],
            "venues": []
        })

    # get number of upcoming shows for each venue
    for venue in venues:
        num_upcoming_shows = 0

        shows = Show.query.filter_by(venue_id=venue.id).all()

        # if the show start time is after now, add to upcoming
        for show in shows:
            if show.start_time > datetime.now():
                num_upcoming_shows += 1

        # for each entry, add venues to matching city/state
        for entry in data:
            if venue.city == entry['city'] and venue.state == entry['state']:
                entry['venues'].append({
                    "id": venue.id,
                    "name": venue.name,
                    "num_upcoming_shows": num_upcoming_shows
                })

    # return venues page with data
    return render_template('pages/venues.html', areas=data)

# venues search route handler
@app.route('/venues/search', methods=['POST'])
def search_venues():
    # get the user search term
    search_term = request.form.get('search_term', '')

    # find all venues matching search term
    # including partial match and case-insensitive
    venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()

    response = {
        "count": len(venues),
        "data": []
    }

    for venue in venues:
        num_upcoming_shows = 0

        shows = Show.query.filter_by(venue_id=venue.id).all()

        # calculuate num of upcoming shows for each venue
        for show in shows:
            if show.start_time > datetime.now():
                num_upcoming_shows += 1

        # add venue data to response
        response['data'].append({
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": num_upcoming_shows,
        })

    # return response with search results
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

# route handler for individual venue pages
@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # get all venues
    venue = Venue.query.filter_by(id=venue_id).first()

    # get all shows for given venue
    shows = Show.query.filter_by(venue_id=venue_id).all()

    # returns upcoming shows
    def upcoming_shows():
        upcoming = []

        # if show is in future, add show details to upcoming
        for show in shows:
            if show.start_time > datetime.now():
                upcoming.append({
                    "artist_id": show.artist_id,
                    "artist_name": Artist.query.filter_by(id=show.artist_id).first().name,
                    "artist_image_link": Artist.query.filter_by(id=show.artist_id).first().image_link,
                    "start_time": format_datetime(str(show.start_time))
                })
        return upcoming

    # returns past shows
    def past_shows():
        past = []

        # if show is in past, add show details to past
        for show in shows:
            if show.start_time < datetime.now():
                past.append({
                    "artist_id": show.artist_id,
                    "artist_name": Artist.query.filter_by(id=show.artist_id).first().name,
                    "artist_image_link": Artist.query.filter_by(id=show.artist_id).first().image_link,
                    "start_time": format_datetime(str(show.start_time))
                })
        return past

    # data for given venue
    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": past_shows(),
        "upcoming_shows": upcoming_shows(),
        "past_shows_count": len(past_shows()),
        "upcoming_shows_count": len(upcoming_shows())
    }

    # return template with venue data
    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

# get the create venue form
@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)

# post handler for venue creation
@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

    # use try-except block to catch exceptions
    try:
        # load data from user input on submit
        form = VenueForm()
        name = form.name.data
        city = form.city.data
        state = form.state.data
        address = form.address.data
        phone = form.phone.data
        # validate phone number -- raises exception if invalid
        phone_validator(phone)
        genres = form.genres.data
        facebook_link = form.facebook_link.data
        website = form.website.data
        image_link = form.image_link.data
        seeking_talent = True if form.seeking_talent.data == 'Yes' else False
        seeking_description = form.seeking_description.data

        # create new Venue from form data
        venue = Venue(name=name, city=city, state=state, address=address,
                      phone=phone, genres=genres, facebook_link=facebook_link,
                      website=website, image_link=image_link,
                      seeking_talent=seeking_talent,
                      seeking_description=seeking_description)

        # add new venue to session and commit to database
        db.session.add(venue)
        db.session.commit()

        # flash success if no errors/exceptions
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except ValidationError as e:
        # ValidationError will be raised if phone num is invalid
        # rollback session and flash error with exception message
        db.session.rollback()
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be listed. ' + str(e))
    except:
        # catches all other exceptions
        db.session.rollback()
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be listed.')
    finally:
        # always close the session
        db.session.close()

    # render home template
    return render_template('pages/home.html')

# route handler for deleting venues
@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    # catch exceptions with try-except block
    try:
        # get venue, delete it, commit to db

        venue = Venue.query.filter(Venue.id == venue_id).first()
        # print('Venue', venue)
        name = venue.name

        db.session.delete(venue)
        db.session.commit()

        # flash if successful delete
        flash('Venue ' + name + ' was successfully deleted.')
    except:

        print("Oops!", sys.exc_info()[0], "occured.")

        # rollback session if exception raised, flash error
        db.session.rollback()

        flash('An error occurred. Venue ' + name + ' could not be deleted.')
    finally:
        # always close the session
        db.session.close()

    # if not error:
    #     return redirect(url_for('index'))
    # else:
    #     abort(500)

    # return success
    return jsonify({'success': True})

#  Artists
#  ----------------------------------------------------------------

# route handler for artists overview page
@app.route('/artists')
def artists():
    # get all artists, return data with name & id of each artist

    data = []

    artists = Artist.query.all()

    for artist in artists:
        data.append({
            "id": artist.id,
            "name": artist.name
        })

    return render_template('pages/artists.html', artists=data)

# artist search route handler
@app.route('/artists/search', methods=['POST'])
def search_artists():

    # get search term from user input
    search_term = request.form.get('search_term', '')

    # find all artists matching search term
    # including partial match and case-insensitive
    artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()

    response = {
        "count": len(artists),
        "data": []
    }

    # for all matching artists, get num of upcoming shows
    # and add data to reponse
    for artist in artists:
        num_upcoming_shows = 0

        shows = Show.query.filter_by(artist_id=artist.id).all()

        for show in shows:
            if show.start_time > datetime.now():
                num_upcoming_shows += 1

        response['data'].append({
            "id": artist.id,
            "name": artist.name,
            "num_upcoming_shows": num_upcoming_shows,
        })

    # return reponse with matching search results
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

# route handler for individual artist pages
@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

    # get artist by id
    artist = Artist.query.filter_by(id=artist_id).first()

    # get all shows matching artist id
    shows = Show.query.filter_by(artist_id=artist_id).all()

    # returns upcoming shows
    def upcoming_shows():
        upcoming = []

        # if the show is upcoming, add to upcoming
        for show in shows:
            if show.start_time > datetime.now():
                upcoming.append({
                    "venue_id": show.venue_id,
                    "venue_name": Venue.query.filter_by(id=show.venue_id).first().name,
                    "venue_image_link": Venue.query.filter_by(id=show.venue_id).first().image_link,
                    "start_time": format_datetime(str(show.start_time))
                })
        return upcoming

    # returns past shows
    def past_shows():
        past = []

        # if show is in past, add to past
        for show in shows:
            if show.start_time < datetime.now():
                past.append({
                    "venue_id": show.venue_id,
                    "venue_name": Venue.query.filter_by(id=show.venue_id).first().name,
                    "venue_image_link": Venue.query.filter_by(id=show.venue_id).first().image_link,
                    "start_time": format_datetime(str(show.start_time))
                })
        return past

    # data for given artist
    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "past_shows": past_shows(),
        "upcoming_shows": upcoming_shows(),
        "past_shows_count": len(past_shows()),
        "upcoming_shows_count": len(upcoming_shows()),
    }

    # return artist page with data
    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------

# route handler for GET edit artist form
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()

    # get the matching artist by id
    artist = Artist.query.filter_by(id=artist_id).first()

    # artist data
    artist = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link
    }

    # set placeholders in form SelectField dropdown menus to current data
    form.state.process_data(artist['state'])
    form.genres.process_data(artist['genres'])
    form.seeking_venue.process_data(artist['seeking_venue'])

    # return edit template with artist data
    return render_template('forms/edit_artist.html', form=form, artist=artist)

# edit artist POST handler
@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):

    # catch exceptions with try-except block
    try:
        form = ArtistForm()

        # get the current artist by id
        artist = Artist.query.filter_by(id=artist_id).first()

        # load data from user input on form submit
        artist.name = form.name.data
        artist.genres = form.genres.data
        artist.city = form.city.data
        artist.state = form.state.data
        artist.phone = form.phone.data
        # validate phone
        phone_validator(artist.phone)
        artist.facebook_link = form.facebook_link.data
        artist.image_link = form.image_link.data
        artist.website = form.website.data
        artist.seeking_venue = True if form.seeking_venue.data == 'Yes' else False
        artist.seeking_description = form.seeking_description.data

        # commit the changes
        db.session.commit()

        flash('Artist ' + request.form['name'] + ' was successfully updated!')
    except ValidationError as e:
        # catch validation errors from phone number

        # rollback session in the event of an exception
        db.session.rollback()
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be listed. ' + str(e))
    except:
        # catch all other exceptions

        db.session.rollback()
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be updated.')
    finally:
        # always close the session
        db.session.close()

    # return redirect to artist page
    return redirect(url_for('show_artist', artist_id=artist_id))

# handler for venue edit GET
@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()

    # get the venue by id
    venue = Venue.query.filter_by(id=venue_id).first()

    # load venue data
    venue = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link
    }

    # set placeholders in form SelectField dropdown menus to current data
    form.state.process_data(venue['state'])
    form.genres.process_data(venue['genres'])
    form.seeking_talent.process_data(venue['seeking_talent'])

    # return edit template with current data
    return render_template('forms/edit_venue.html', form=form, venue=venue)

# venue edit POST handler
@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):

    # catch exceptions with try-except block
    try:
        form = VenueForm()

        # get venue by id
        venue = Venue.query.filter_by(id=venue_id).first()

        # load form data from user input
        venue.name = form.name.data
        venue.genres = form.genres.data
        venue.city = form.city.data
        venue.state = form.state.data
        venue.address = form.address.data
        venue.phone = form.phone.data
        # validate phone num
        phone_validator(venue.phone)
        venue.facebook_link = form.facebook_link.data
        venue.website = form.website.data
        venue.image_link = form.image_link.data
        venue.seeking_talent = True if form.seeking_talent.data == 'Yes' else False
        venue.seeking_description = form.seeking_description.data

        # commit changes, flash message if successful
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully updated!')
    except ValidationError as e:
        # catch errors from phone validation

        # rollback session if error
        db.session.rollback()
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be listed. ' + str(e))
    except:
        # catch all other errors
        db.session.rollback()
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be updated.')
    finally:
        # always close the session
        db.session.close()

    # return redirect to venue page
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

# artist creation GET route handler
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()

    # return the new artist form
    return render_template('forms/new_artist.html', form=form)

# artist creation POST handler
@app.route('/artists/create', methods=['POST'])
def create_artist_submission():

    # catch exceptions with try-except block
    try:
        form = ArtistForm()
        name = form.name.data
        city = form.city.data
        state = form.state.data
        phone = form.phone.data
        # validate phone
        phone_validator(phone)
        genres = form.genres.data
        facebook_link = form.facebook_link.data
        website = form.website.data
        image_link = form.image_link.data
        seeking_venue = True if form.seeking_venue.data == 'Yes' else False
        seeking_description = form.seeking_description.data

        # create new artist from form data
        artist = Artist(name=name, city=city, state=state, phone=phone,
                        genres=genres, facebook_link=facebook_link,
                        website=website, image_link=image_link,
                        seeking_venue=seeking_venue,
                        seeking_description=seeking_description)

        # add new artist and commit session
        db.session.add(artist)
        db.session.commit()

        # flash message if successful
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except ValidationError as e:
        # catch validation error from phone, rollback changes

        db.session.rollback()
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be listed. ' + str(e))
    except:
        # catch all other exceptions
        db.session.rollback()
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be listed.')
    finally:
        # always close the session
        db.session.close()

    # return template for home page
    return render_template('pages/home.html')

# delete artist route handler
@app.route('/artists/<int:artist_id>', methods=['DELETE'])
def delete_artist(artist_id):

    # catch exceptions with try-except block
    try:
        # get artist by id
        artist = Artist.query.filter_by(id=artist_id).first()
        name = artist.name

        # delete artist and commit changes
        db.session.delete(artist)
        db.session.commit()

        flash('Artist ' + name + ' was successfully deleted.')
    except:
        # rollback if exception
        db.session.rollback()

        flash('An error occurred. Artist ' + name + ' could not be deleted.')
    finally:
        # always close the session
        db.session.close()

    return jsonify({'success': True})


#  Shows
#  ----------------------------------------------------------------

# route handler for shows page
@app.route('/shows')
def shows():

    # get all the shows
    shows = Show.query.all()

    data = []

    # get venue and artist information for each show
    for show in shows:
        data.append({
            "venue_id": show.venue_id,
            "venue_name": Venue.query.filter_by(id=show.venue_id).first().name,
            "artist_id": show.artist_id,
            "artist_name": Artist.query.filter_by(id=show.artist_id).first().name,
            "artist_image_link": Artist.query.filter_by(id=show.artist_id).first().image_link,
            "start_time": format_datetime(str(show.start_time))
        })

    # return shows page with show data
    return render_template('pages/shows.html', shows=data)

# handler for rendering create shows page
@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)

# POST handler for show create
@app.route('/shows/create', methods=['POST'])
def create_show_submission():

    # catch exceptions with try-except block
    try:
        # get user input data from form
        artist_id = request.form['artist_id']
        venue_id = request.form['venue_id']
        start_time = request.form['start_time']

        # create new show with user data
        show = Show(artist_id=artist_id, venue_id=venue_id,
                    start_time=start_time)

        # add show and commit session
        db.session.add(show)
        db.session.commit()

        # on successful db insert, flash success
        flash('Show was successfully listed!')
    except:
        # rollback if exception
        db.session.rollback()

        flash('An error occurred. Show could not be listed.')
    finally:
        db.session.close()

    # return homepage template
    return render_template('pages/home.html')

# error handlers


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''