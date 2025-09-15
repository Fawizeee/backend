from datetime import datetime, timezone
from models import db, User, Event, EventAttendee, Notification, Comment
from sqlalchemy.exc import SQLAlchemyError
from flask import jsonify
from push_notifications import push_notification_service

class EventService:
    @staticmethod
    def create_event(user_id, data):
        """Create a new event with validation"""
        try:
            # Convert string values to appropriate types
            user = User.query.get(user_id)  # Ensure user exists
            max_attendees = int(data.get('max_attendees', 50))
            
            # Parse dates from string to datetime
            try:
                start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
            except ValueError:
                return None, {'error': 'Invalid date format'}, 400

            # Create new event with proper data types
            event = Event(
                title=str(data['title']),
                description=str(data['description']),
                location=str(data['location']),
                start_date=start_date,
                end_date=end_date,
                created_by=int(user_id),
                university='Student Event Network',  # Default since user.university no longer exists
                image=str(data.get('image', '')),
                max_attendees=max_attendees,
                current_attendees=0,
                tags=data.get('tags', [])
            )
            
            db.session.add(event)
            db.session.commit()
            
            return event, {'message': 'Event created successfully'}, 201
            
        except ValueError as e:
            db.session.rollback()
            return None, {'error': f'Invalid data format: {str(e)}'}, 400
        except Exception as e:
            db.session.rollback()
            return None, {'error': str(e)}, 500
    
    @staticmethod
    def update_event(event_id, user_id, event_data):
        """Update an existing event"""
        try:
            event = Event.query.get(event_id)
            if not event:
                return None, {'error': 'Event not found'}, 404
            
            if event.created_by != user_id:
                return None, {'error': 'Unauthorized'}, 403
            
            # Update fields
            allowed_fields = ['title', 'description', 'location', 'tags', 'image']
            for field in allowed_fields:
                if field in event_data:
                    setattr(event, field, event_data[field])
            
            # Handle max_attendees separately to ensure proper type conversion
            if 'max_attendees' in event_data:
                try:
                    event.max_attendees = int(event_data['max_attendees'])
                except (ValueError, TypeError):
                    return None, {'error': 'Invalid max_attendees value'}, 400
            
            # Handle date updates with validation
            if 'start_date' in event_data:
                try:
                    start_date = datetime.fromisoformat(event_data['start_date'].replace('Z', '+00:00'))
                    event.start_date = start_date
                except ValueError:
                    return None, {'error': 'Invalid start date format'}, 400
            
            if 'end_date' in event_data:
                try:
                    end_date = datetime.fromisoformat(event_data['end_date'].replace('Z', '+00:00'))
                    event.end_date = end_date
                except ValueError:
                    return None, {'error': 'Invalid end date format'}, 400
            
            event.updated_at = datetime.utcnow().replace(tzinfo=timezone.utc)
            
            # Create notifications for all attendees when event is edited
            attendees = EventAttendee.query.filter_by(event_id=event_id).all()
            for attendee in attendees:
                notification = Notification(
                    user_id=attendee.user_id,
                    event_id=event_id,
                    type='event_edited',
                    message=f'The event "{event.title}" has been updated by the organizer.'
                )
                db.session.add(notification)
            
            db.session.commit()
            
            # Send push notifications
            attendee_user_ids = [attendee.user_id for attendee in attendees]
            push_notification_service.send_event_edit_notification(event_id, event.title, attendee_user_ids)
            
            return event, {'message': 'Event updated successfully'}, 200
            
        except ValueError as e:
            return None, {'error': str(e)}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, {'error': 'Database error: ' + str(e)}, 500
    
    @staticmethod
    def register_for_event(event_id, user_id):
        """Register a user for an event"""
        try:
            event = Event.query.get(event_id)
            if not event or not event.is_active:
                return None, {'error': 'Event not found or inactive'}, 404
            
            if not event.can_register():
                return None, {'error': 'Cannot register for this event'}, 400
            
            # Check if already registered
            existing_attendance = EventAttendee.query.filter_by(
                event_id=event_id, user_id=user_id
            ).first()
            
            if existing_attendance:
                return None, {'error': 'Already registered for this event'}, 409
            
            # Create attendance record
            attendance = EventAttendee(event_id=event_id, user_id=user_id)
            event.current_attendees += 1
            
            db.session.add(attendance)
            db.session.commit()
            
            return attendance, {'message': 'Successfully registered for event'}, 201
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, {'error': 'Database error: ' + str(e)}, 500
    
    @staticmethod
    def unregister_from_event(event_id, user_id):
        """Unregister a user from an event"""
        try:
            attendance = EventAttendee.query.filter_by(
                event_id=event_id, user_id=user_id
            ).first()
            
            if not attendance:
                return None, {'error': 'Not registered for this event'}, 404
            
            event = Event.query.get(event_id)
            if event:
                event.current_attendees -= 1
            
            db.session.delete(attendance)
            db.session.commit()
            
            return True, {'message': 'Successfully unregistered from event'}, 200
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, {'error': 'Database error: ' + str(e)}, 500
    
    @staticmethod
    def get_event_attendees(event_id):
        """Get all attendees for an event"""
        try:
            event = Event.query.get(event_id)
            if not event:
                return None, {'error': 'Event not found'}, 404
            
            attendees = EventAttendee.query.filter_by(event_id=event_id)\
                .join(User)\
                .order_by(EventAttendee.registered_at.asc()).all()
            
            return attendees, None, 200
            
        except SQLAlchemyError as e:
            return None, {'error': 'Database error: ' + str(e)}, 500

class UserService:
    @staticmethod
    def get_user_events(user_id):
        """Get events created by a user"""
        try:
            events = Event.query.filter_by(created_by=user_id, is_active=True)\
                .order_by(Event.start_date.asc()).all()
            return events, None, 200
        except SQLAlchemyError as e:
            return None, {'error': 'Database error: ' + str(e)}, 500

class NotificationService:
    @staticmethod
    def get_user_notifications(user_id):
        """Get all notifications for a user"""
        try:
            notifications = Notification.query.filter_by(user_id=user_id)\
                .order_by(Notification.created_at.desc()).all()
            return notifications, None, 200
        except SQLAlchemyError as e:
            return None, {'error': 'Database error: ' + str(e)}, 500
    
    @staticmethod
    def mark_notification_as_read(notification_id, user_id):
        """Mark a notification as read"""
        try:
            notification = Notification.query.get(notification_id)
            if not notification:
                return None, {'error': 'Notification not found'}, 404
            
            if notification.user_id != user_id:
                return None, {'error': 'Unauthorized'}, 403
            
            notification.is_read = True
            db.session.commit()
            
            return notification, {'message': 'Notification marked as read'}, 200
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, {'error': 'Database error: ' + str(e)}, 500
    
    @staticmethod
    def mark_all_notifications_as_read(user_id):
        """Mark all notifications as read for a user"""
        try:
            notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
            for notification in notifications:
                notification.is_read = True
            
            db.session.commit()
            
            return True, {'message': 'All notifications marked as read'}, 200
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, {'error': 'Database error: ' + str(e)}, 500
    
    @staticmethod
    def create_event_reminder_notifications():
        """Create reminder notifications for events starting soon"""
        try:
            from datetime import timedelta
            
            # Get events starting in the next 24 hours
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            tomorrow = now + timedelta(hours=24)
            day_before = now + timedelta(hours=1)  # 1 hour before
            
            # Events starting in 1 hour (event_starting)
            starting_soon_events = Event.query.filter(
                Event.start_date >= now,
                Event.start_date <= day_before,
                Event.is_active == True
            ).all()
            
            # Events starting in 24 hours (event_soon)
            upcoming_events = Event.query.filter(
                Event.start_date >= day_before,
                Event.start_date <= tomorrow,
                Event.is_active == True
            ).all()
            
            notifications_created = 0
            
            # Create notifications for events starting in 1 hour
            for event in starting_soon_events:
                attendees = EventAttendee.query.filter_by(event_id=event.id).all()
                for attendee in attendees:
                    # Check if notification already exists
                    existing = Notification.query.filter_by(
                        user_id=attendee.user_id,
                        event_id=event.id,
                        type='event_starting'
                    ).first()
                    
                    if not existing:
                        notification = Notification(
                            user_id=attendee.user_id,
                            event_id=event.id,
                            type='event_starting',
                            message=f'🚀 "{event.title}" is starting in 1 hour!'
                        )
                        db.session.add(notification)
                        notifications_created += 1
            
            # Create notifications for events starting in 24 hours
            for event in upcoming_events:
                attendees = EventAttendee.query.filter_by(event_id=event.id).all()
                for attendee in attendees:
                    # Check if notification already exists
                    existing = Notification.query.filter_by(
                        user_id=attendee.user_id,
                        event_id=event.id,
                        type='event_soon'
                    ).first()
                    
                    if not existing:
                        notification = Notification(
                            user_id=attendee.user_id,
                            event_id=event.id,
                            type='event_soon',
                            message=f'📅 "{event.title}" is tomorrow! Don\'t forget to attend.'
                        )
                        db.session.add(notification)
                        notifications_created += 1
            
            db.session.commit()
            
            # Send push notifications for reminders
            push_success, push_result = push_notification_service.send_reminder_notifications()
            if push_success:
                print(f"Push notifications sent: {push_result}")
            else:
                print(f"Push notification error: {push_result}")
            
            return notifications_created, None, 200
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, {'error': 'Database error: ' + str(e)}, 500

    @staticmethod
    def get_user_registered_events(user_id):
        """Get events a user is registered for"""
        try:
            attendances = EventAttendee.query.filter_by(user_id=user_id)\
                .join(Event)\
                .filter(Event.is_active == True)\
                .order_by(Event.start_date.asc()).all()
            
            events = [attendance.event for attendance in attendances]
            return events, None, 200
        except SQLAlchemyError as e:
            return None, {'error': 'Database error: ' + str(e)}, 500

class EventQueryService:
    @staticmethod
    def get_events_with_filters(filters):
        """Get events with various filters"""
        try:
            query = Event.query.filter_by(is_active=True)
            
            if filters.get('tags'):
                # Filter events that have at least one matching tag
                user_tags = filters['tags']
                if isinstance(user_tags, str):
                    user_tags = [tag.strip() for tag in user_tags.split(',')]
                
                # For SQLite JSON queries, we need to search differently
                # Get all events first and filter in Python for better reliability
                all_events = query.all()
                matching_events = []
                
                for event in all_events:
                    if event.tags:
                        # Handle both array and string tag formats
                        if isinstance(event.tags, list):
                            event_tags_lower = [tag.lower() if tag else '' for tag in event.tags]
                        elif isinstance(event.tags, str):
                            # Split comma-separated string tags
                            event_tags_lower = [tag.strip().lower() for tag in event.tags.split(',') if tag.strip()]
                        else:
                            continue
                        
                        for user_tag in user_tags:
                            if user_tag.lower() in event_tags_lower:
                                matching_events.append(event)
                                break
                
                if matching_events:
                    event_ids = [event.id for event in matching_events]
                    query = Event.query.filter(Event.id.in_(event_ids), Event.is_active == True)
                else:
                    # No matches found
                    query = Event.query.filter(Event.id == -1)
            
            # Category filtering removed - using tags instead
            
            if filters.get('search'):
                search_term = filters['search']
                search_term_like = f"%{search_term}%"
                
                # Handle hashtag search - remove # if present
                tag_search_term = search_term.lstrip('#').lower()
                
                # For SQLite, we need to handle JSON tag search differently
                # Start with the base query (which may already have filters applied)
                base_query = query
                
                # Search in title and description
                title_desc_query = base_query.filter(
                    (Event.title.ilike(search_term_like)) | 
                    (Event.description.ilike(search_term_like))
                )
                title_desc_events = title_desc_query.all()
                
                # Search in tags - get all events that match base filters first
                all_filtered_events = base_query.all()
                
                # Filter events by tags in Python
                tag_matching_events = []
                for event in all_filtered_events:
                    if event.tags:
                        # Handle both array and string tag formats
                        if isinstance(event.tags, list):
                            for tag in event.tags:
                                if tag and isinstance(tag, str) and tag_search_term in tag.lower():
                                    tag_matching_events.append(event)
                                    break
                        elif isinstance(event.tags, str):
                            # Split comma-separated string tags
                            string_tags = [tag.strip() for tag in event.tags.split(',') if tag.strip()]
                            for tag in string_tags:
                                if tag_search_term in tag.lower():
                                    tag_matching_events.append(event)
                                    break
                
                # Combine results and remove duplicates
                all_matching_events = []
                seen_ids = set()
                
                for event in title_desc_events + tag_matching_events:
                    if event.id not in seen_ids:
                        all_matching_events.append(event)
                        seen_ids.add(event.id)
                
                # Create a new query that matches only these event IDs
                if all_matching_events:
                    event_ids = [event.id for event in all_matching_events]
                    query = Event.query.filter(Event.id.in_(event_ids), Event.is_active == True)
                else:
                    # No matches found - return empty result
                    query = Event.query.filter(Event.id == -1)
            
            # Filter by date range if provided
            if filters.get('start_date_after'):
                start_date_str = filters['start_date_after']
                if not start_date_str.endswith('Z') and '+' not in start_date_str and start_date_str.count('T') > 0:
                    start_date_str += '+00:00'  # Add UTC timezone if not present
                start_date = datetime.fromisoformat(start_date_str)
                query = query.filter(Event.start_date >= start_date)
            
            if filters.get('end_date_before'):
                end_date_str = filters['end_date_before']
                if not end_date_str.endswith('Z') and '+' not in end_date_str and end_date_str.count('T') > 0:
                    end_date_str += '+00:00'  # Add UTC timezone if not present
                end_date = datetime.fromisoformat(end_date_str)
                query = query.filter(Event.end_date <= end_date)
            
            # Order by start date
            events = query.order_by(Event.start_date.asc()).all()
            
            return events, None, 200
            
        except ValueError as e:
            return None, {'error': 'Invalid date format'}, 400
        except SQLAlchemyError as e:
            return None, {'error': 'Database error: ' + str(e)}, 500

class CommentService:
    @staticmethod
    def create_comment(event_id, user_id, content):
        """Create a new comment on an event"""
        try:
            # Validate that the event exists and is active
            event = Event.query.get(event_id)
            if not event or not event.is_active:
                return None, {'error': 'Event not found or inactive'}, 404

            # Create the comment
            comment = Comment(
                event_id=event_id,
                user_id=user_id,
                content=str(content).strip()
            )

            if len(comment.content) < 1:
                return None, {'error': 'Comment cannot be empty'}, 400

            db.session.add(comment)
            db.session.commit()

            # Create notifications for all attendees (except the commenter)
            attendees = EventAttendee.query.filter_by(event_id=event_id).all()
            # Get the commenter's name for notifications
            commenter = User.query.get(user_id)
            commenter_name = f"{commenter.first_name} {commenter.last_name}" if commenter else "Unknown User"
            
            for attendee in attendees:
                if attendee.user_id != user_id:  # Don't notify the commenter
                    notification = Notification(
                        user_id=attendee.user_id,
                        event_id=event_id,
                        type='new_comment',
                        message=f'New comment on "{event.title}" by {commenter_name}'
                    )
                    db.session.add(notification)

            db.session.commit()
            
            # Send push notifications
            attendee_user_ids = [attendee.user_id for attendee in attendees if attendee.user_id != user_id]
            push_notification_service.send_comment_notification(event_id, commenter_name, event.title, attendee_user_ids)

            return comment, {'message': 'Comment created successfully'}, 201

        except SQLAlchemyError as e:
            db.session.rollback()
            return None, {'error': 'Database error: ' + str(e)}, 500

    @staticmethod
    def get_event_comments(event_id):
        """Get all comments for an event"""
        try:
            comments = Comment.query.filter_by(event_id=event_id)\
                .join(User)\
                .order_by(Comment.created_at.asc()).all()
            return comments, None, 200
        except SQLAlchemyError as e:
            return None, {'error': 'Database error: ' + str(e)}, 500

    @staticmethod
    def delete_comment(comment_id, user_id):
        """Delete a comment"""
        try:
            comment = Comment.query.get(comment_id)
            if not comment:
                return None, {'error': 'Comment not found'}, 404

            if comment.user_id != user_id:
                return None, {'error': 'Unauthorized'}, 403

            db.session.delete(comment)
            db.session.commit()

            return True, {'message': 'Comment deleted successfully'}, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            return None, {'error': 'Database error: ' + str(e)}, 500
