#!/usr/bin/env python3

from flask import request, session
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError

from config import app, db, api
from models import User, Recipe, UserSchema, RecipeSchema

class Signup(Resource):

    def post(self):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {'errors': ['A JSON request body is required']}, 422

        if not data.get('username'):
            return {'errors': ['Username is required']}, 422
        if not data.get('password'):
            return {'errors': ['Password is required']}, 422

        try:
            user = User(
                username=data['username'],
                image_url=data.get('image_url'),
                bio=data.get('bio'),
            )
            user.password_hash = data['password']
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {'errors': ['Username must be unique']}, 422
        except ValueError as error:
            db.session.rollback()
            return {'errors': [str(error)]}, 422

        session['user_id'] = user.id
        return UserSchema().dump(user), 201

class CheckSession(Resource):

    def get(self):
        user_id = session.get('user_id')
        user = db.session.get(User, user_id) if user_id is not None else None
        if user is None:
            session.pop('user_id', None)
            return {'errors': ['Unauthorized']}, 401

        return UserSchema().dump(user), 200

class Login(Resource):

    def post(self):
        data = request.get_json(silent=True)
        username = data.get('username') if isinstance(data, dict) else None
        password = data.get('password') if isinstance(data, dict) else None
        user = User.query.filter_by(username=username).first()

        if user is None or not isinstance(password, str) or not user.authenticate(password):
            session.pop('user_id', None)
            return {'errors': ['Invalid username or password']}, 401

        session['user_id'] = user.id
        return UserSchema().dump(user), 200

class Logout(Resource):

    def delete(self):
        user_id = session.get('user_id')
        if user_id is None:
            return {'errors': ['Unauthorized']}, 401

        session.pop('user_id', None)
        return {}, 204

class RecipeIndex(Resource):

    def get(self):
        user_id = session.get('user_id')
        user = db.session.get(User, user_id) if user_id is not None else None
        if user is None:
            session.pop('user_id', None)
            return {'errors': ['Unauthorized']}, 401

        recipes = Recipe.query.filter_by(user_id=user.id).all()
        return [RecipeSchema().dump(recipe) for recipe in recipes], 200

    def post(self):
        user_id = session.get('user_id')
        user = db.session.get(User, user_id) if user_id is not None else None
        if user is None:
            session.pop('user_id', None)
            return {'errors': ['Unauthorized']}, 401

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {'errors': ['A JSON request body is required']}, 422

        try:
            recipe = Recipe(
                title=data.get('title'),
                instructions=data.get('instructions'),
                minutes_to_complete=data.get('minutes_to_complete'),
                user=user,
            )
            db.session.add(recipe)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {'errors': ['Recipe is invalid']}, 422
        except ValueError as error:
            db.session.rollback()
            return {'errors': [str(error)]}, 422

        return RecipeSchema().dump(recipe), 201

api.add_resource(Signup, '/signup', endpoint='signup')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Logout, '/logout', endpoint='logout')
api.add_resource(RecipeIndex, '/recipes', endpoint='recipes')


if __name__ == '__main__':
    app.run(port=5555, debug=True)