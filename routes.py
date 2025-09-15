from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from models import db, User, Event, EventAttendee
from services import EventService, UserService, EventQueryService, NotificationService, CommentService
from constants import PREDEFINED_TAGS

def register_routes(app):
    # Auth Routes
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['email', 'password', 'first_name', 'last_name', 'tags']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} is required'}), 400
            
            # Validate tags
            tags = data.get('tags', [])
            if not isinstance(tags, list) or len(tags) < 3:
                return jsonify({'error': 'At least 3 tags must be selected'}), 400
            
            # Check if user already exists
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email already registered'}), 409
            
            # Hash password
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt(app)
            password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
            
            # Create new user
            user = User(
                email=data['email'],
                password_hash=password_hash,
                first_name=data['first_name'],
                last_name=data['last_name'],
                tags=tags,
                major=data.get('major', ''),
                year=data.get('year', ''),
                bio=data.get('bio', '')
            )
            
            db.session.add(user)
            db.session.commit()
            
            # Create token
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity=user.id)
            
            return jsonify({
                'message': 'User registered successfully',
                'token': access_token,
                'user': user.to_dict()
            }), 201
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        try:
            data = request.get_json()
            
            if not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Email and password are required'}), 400
            
            # Find user
            user = User.query.filter_by(email=data['email']).first()
            
            if not user:
                return jsonify({'error': 'Invalid email or password'}), 401
            
            # Verify password
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt(app)
            if not bcrypt.check_password_hash(user.password_hash, data['password']):
                return jsonify({'error': 'Invalid email or password'}), 401
            
            # Create token
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity=user.id)
            
            return jsonify({
                'message': 'Login successful',
                'token': access_token,
                'user': user.to_dict()
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/auth/me', methods=['GET'])
    @jwt_required()
    def get_current_user():
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
                
            return jsonify({'user': user.to_dict()}), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/auth/update-profile', methods=['PUT'])
    @jwt_required()
    def update_profile():
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            data = request.get_json()
            
            # Update allowed fields
            allowed_fields = ['first_name', 'last_name', 'major', 'year', 'bio', 'profile_picture']
            for field in allowed_fields:
                if field in data:
                    setattr(user, field, data[field])
            
            user.updated_at = datetime.utcnow().replace(tzinfo=timezone.utc)
            db.session.commit()
            
            return jsonify({
                'message': 'Profile updated successfully',
                'user': user.to_dict()
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/tags', methods=['GET'])
    def get_tags():
        try:
            return jsonify({'tags': PREDEFINED_TAGS}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Event Routes
    @app.route('/api/events', methods=['GET'])
    @jwt_required()
    def get_events():
        try:
            filters = {
                'tags': request.args.get('tags'),
                'search': request.args.get('search'),
                'start_date_after': request.args.get('start_date_after'),
                'end_date_before': request.args.get('end_date_before')
            }
            
            events, error, status = EventQueryService.get_events_with_filters(filters)
            if error:
                return jsonify(error), status
            
            return jsonify({
                'events': [event.to_dict() for event in events]
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/events', methods=['POST'])
    @jwt_required()
    def create_event():
        try:
            user_id = get_jwt_identity()
            
            # Handle both multipart form data and JSON
            if 'multipart/form-data' in request.content_type:
                data = request.form.to_dict()
                image_file = request.files.get('image')
            else:
                data = request.get_json()
                image_file = None

            # Validate required fields  
            required_fields = ['title', 'description', 'location', 'start_date', 'end_date']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} is required'}), 400
            
            # Process image if present
            if image_file:
                try:
                    import os
                    from werkzeug.utils import secure_filename
                    upload_folder = app.config['UPLOAD_FOLDER']
                    os.makedirs(upload_folder, exist_ok=True)
                    filename = secure_filename(image_file.filename)
                    filepath = os.path.join(upload_folder, filename)
                    image_file.save(filepath)
                    # Add image path to data dictionary
                    data['image'] = f'/static/uploads/{filename}'
                except Exception as e:
                    return jsonify({'error': f'Error uploading image: {str(e)}'}), 500

            # Create event using service
            event, result, status = EventService.create_event(user_id, data)
            
            if not event:
                # If image was uploaded but event creation failed, delete the image
                if image_file and 'image' in data:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], data['image'].split('/')[-1]))
                    except:
                        pass  # Ignore cleanup errors
                return jsonify(result), status

            return jsonify({
                'message': result['message'],
                'event': event.to_dict()
            }), status

        except Exception as e:
            # Cleanup uploaded image if exists but event creation failed
            if 'image' in locals() and 'data' in locals() and 'image' in data:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], data['image'].split('/')[-1]))
                except:
                    pass
            return jsonify({'error': str(e)}), 500

    @app.route('/api/events/<int:event_id>', methods=['GET'])
    @jwt_required()
    def get_event(event_id):
        try:
            event = Event.query.get_or_404(event_id)
            return jsonify({'event': event.to_dict()}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/events/<int:event_id>', methods=['PUT'])
    @jwt_required()
    def update_event(event_id):
        try:
            user_id = get_jwt_identity()
            # For image upload, expect multipart/form-data
            if 'multipart/form-data' in request.content_type:
                data = request.form.to_dict()
                image_file = request.files.get('image')
            else:
                data = request.get_json()
                image_file = None

            # Handle image saving if image_file is present
            if image_file:
                import os
                from werkzeug.utils import secure_filename
                upload_folder = app.config['UPLOAD_FOLDER']
                os.makedirs(upload_folder, exist_ok=True)
                filename = secure_filename(image_file.filename)
                filepath = os.path.join(upload_folder, filename)
                image_file.save(filepath)
                # Save relative path to DB
                data['image'] = f'/static/uploads/{filename}'

            event, result, status = EventService.update_event(event_id, user_id, data)
            if not event:
                return jsonify(result), status

            return jsonify({
                'message': result['message'],
                'event': event.to_dict()
            }), status

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/events/<int:event_id>', methods=['DELETE'])
    @jwt_required()
    def delete_event(event_id):
        try:
            user_id = get_jwt_identity()
            event = Event.query.get_or_404(event_id)
            
            # Check if user is the creator
            if event.created_by != user_id:
                return jsonify({'error': 'Unauthorized'}), 403
            
            event.is_active = False
            db.session.commit()
            
            return jsonify({'message': 'Event deleted successfully'}), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Event Attendance Routes
    @app.route('/api/events/<int:event_id>/register', methods=['POST'])
    @jwt_required()
    def register_for_event(event_id):
        try:
            user_id = get_jwt_identity()
            
            attendance, result, status = EventService.register_for_event(event_id, user_id)
            if not attendance:
                return jsonify(result), status
            
            return jsonify(result), status
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/events/<int:event_id>/unregister', methods=['POST'])
    @jwt_required()
    def unregister_from_event(event_id):
        try:
            user_id = get_jwt_identity()
            
            success, result, status = EventService.unregister_from_event(event_id, user_id)
            if not success:
                return jsonify(result), status
            
            return jsonify(result), status
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/events/<int:event_id>/attendees', methods=['GET'])
    @jwt_required()
    def get_event_attendees(event_id):
        try:
            attendees, error, status = EventService.get_event_attendees(event_id)
            if error:
                return jsonify(error), status
            
            return jsonify({
                'attendees': [attendee.to_dict() for attendee in attendees]
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Notification Routes
    @app.route('/api/notifications', methods=['GET'])
    @jwt_required()
    def get_notifications():
        user_id = get_jwt_identity()
        notifications, error, status = NotificationService.get_user_notifications(user_id)
        if error:
            return jsonify(error), status
        return jsonify({'notifications': [notification.to_dict() for notification in notifications]}), 200

    @app.route('/api/notifications/<int:notification_id>', methods=['PUT'])
    @jwt_required()
    def mark_notification_as_read(notification_id):
        user_id = get_jwt_identity()
        notification, error, status = NotificationService.mark_notification_as_read(notification_id, user_id)
        if error:
            return jsonify(error), status
        return jsonify(notification.to_dict()), 200

    @app.route('/api/notifications/mark-all', methods=['PUT'])
    @jwt_required()
    def mark_all_notifications_as_read():
        user_id = get_jwt_identity()
        success, message, status = NotificationService.mark_all_notifications_as_read(user_id)
        if not success:
            return jsonify(message), status
        return jsonify(message), 200

    @app.route('/api/notifications/create-reminders', methods=['POST'])
    def create_reminder_notifications():
        """Create reminder notifications for upcoming events (can be called by cron job)"""
        try:
            count, error, status = NotificationService.create_event_reminder_notifications()
            if error:
                return jsonify(error), status
            return jsonify({'message': f'Created {count} reminder notifications'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/notifications/register-device', methods=['POST'])
    @jwt_required()
    def register_device_token():
        """Register device token for push notifications"""
        try:
            user_id = get_jwt_identity()
            data = request.get_json()
            
            device_token = data.get('device_token')
            platform = data.get('platform', 'unknown')
            
            if not device_token:
                return jsonify({'error': 'Device token is required'}), 400
            
            # Store device token in user's profile
            user = User.query.get(user_id)
            if user:
                try:
                    # Update device tokens
                    device_tokens = getattr(user, 'device_tokens', []) or []
                    
                    # Check if token already exists
                    token_exists = any(token_obj.get('token') == device_token for token_obj in device_tokens)
                    
                    if not token_exists:
                        device_tokens.append({
                            'token': device_token,
                            'platform': platform,
                            'registered_at': datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
                        })
                        user.device_tokens = device_tokens
                        db.session.commit()
                        
                        # Register token with push notification service
                        push_notification_service.register_user_token(user_id, device_token)
                        
                        return jsonify({'message': 'Device token registered successfully'}), 200
                    else:
                        return jsonify({'message': 'Device token already registered'}), 200
                        
                except Exception as db_error:
                    # If device_tokens column doesn't exist, just log and return success
                    print(f"Device tokens column not available: {db_error}")
                    return jsonify({'message': 'Device token registration not available'}), 200
            else:
                return jsonify({'error': 'User not found'}), 404
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # User Event Routes
    @app.route('/api/users/me/events', methods=['GET'])
    @jwt_required()
    def get_user_events():
        try:
            user_id = get_jwt_identity()
            
            events, error, status = UserService.get_user_events(user_id)
            if error:
                return jsonify(error), status
            
            return jsonify({
                'events': [event.to_dict() for event in events]
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/users/me/created-events', methods=['GET'])
    @jwt_required()
    def get_user_created_events():
        try:
            user_id = get_jwt_identity()
            
            # Get events created by the user
            events = Event.query.filter_by(created_by=user_id).order_by(Event.created_at.desc()).all()
            
            return jsonify({
                'events': [event.to_dict() for event in events]
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/users/me/registered-events', methods=['GET'])
    @jwt_required()
    def get_user_registered_events():
        try:
            user_id = get_jwt_identity()
            print(f"Getting registered events for user_id: {user_id}")
            
            # Check if user exists
            user = User.query.get(user_id)
            if not user:
                print(f"User not found: {user_id}")
                return jsonify({'error': 'User not found'}), 404
                
            events, error, status = NotificationService.get_user_registered_events(user_id)
            
            if error:
                print(f"Error getting events: {error}")
                return jsonify(error), status
            
            # Debug print the events
            print(f"Found {len(events)} events: {events}")
            
            return jsonify({
                'events': [event.to_dict() for event in events]
            }), 200
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"Exception occurred: {str(e)}")
            print(f"Traceback: {error_traceback}")
            return jsonify({'error': str(e)}), 500

    # Categories Route - Removed (using tags instead)
    # @app.route('/api/events/categories', methods=['GET'])
    # def get_categories():
    #     return jsonify({
    #         'categories': [
    #             'Academic',
    #             'Social',
    #             'Career',
    #             'Workshop',
    #             'Sports',
    #             'Cultural',
    #             'Volunteer',
    #             'Networking'
    #         ]
    #     }), 200

    # Comment Routes
    @app.route('/api/events/<int:event_id>/comments', methods=['GET'])
    @jwt_required()
    def get_event_comments(event_id):
        try:
            comments, error, status = CommentService.get_event_comments(event_id)
            if error:
                return jsonify(error), status
            return jsonify({'comments': [comment.to_dict() for comment in comments]}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/events/<int:event_id>/comments', methods=['POST'])
    @jwt_required()
    def create_comment(event_id):
        try:
            user_id = get_jwt_identity()
            data = request.get_json()

            if not data.get('content'):
                return jsonify({'error': 'Comment content is required'}), 400

            comment, result, status = CommentService.create_comment(event_id, user_id, data['content'])
            if not comment:
                return jsonify(result), status

            return jsonify({
                'message': result['message'],
                'comment': comment.to_dict()
            }), status

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
    @jwt_required()
    def delete_comment(comment_id):
        try:
            user_id = get_jwt_identity()

            success, result, status = CommentService.delete_comment(comment_id, user_id)
            if not success:
                return jsonify(result), status

            return jsonify(result), status

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Health Check Route
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()}), 200
