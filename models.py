from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from sqlalchemy.orm import validates
from sqlalchemy import CheckConstraint

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    tags = db.Column(db.JSON, default=list)  # User's selected tags
    major = db.Column(db.String(100), nullable=True)
    year = db.Column(db.String(20), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc), onupdate=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))
    
    # Relationships
    created_events = db.relationship('Event', backref='creator', lazy=True, foreign_keys='Event.created_by')
    event_attendances = db.relationship('EventAttendee', backref='attendee', lazy=True)
    
    @validates('email')
    def validate_email(self, key, email):
        if '@' not in email:
            raise ValueError('Invalid email format')
        return email
    
    @validates('tags')
    def validate_tags(self, key, tags):
        if not isinstance(tags, list):
            raise ValueError('Tags must be a list')
        if len(tags) < 3:
            raise ValueError('At least 3 tags must be selected')
        if len(tags) > 20:
            raise ValueError('Maximum 20 tags allowed')
        return tags
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'tags': self.tags,
            'major': self.major,
            'year': self.year,
            'bio': self.bio,
            'profile_picture': self.profile_picture,
            'created_at': self.created_at.isoformat()
        }

# Event Model
class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    # category = db.Column(db.String(50), nullable=False)  # Removed - using tags instead
    max_attendees = db.Column(db.Integer, default=50)
    current_attendees = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    university = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(255), nullable=True)  # New field for event image
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc), onupdate=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))
    tags = db.Column(db.JSON, default=list)  # New field for tags

    
    # Relationships
    attendees = db.relationship('EventAttendee', backref='event', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (
        CheckConstraint('end_date > start_date', name='check_end_date_after_start_date'),
        CheckConstraint('max_attendees >= 1', name='check_max_attendees_positive'),
        CheckConstraint('current_attendees >= 0', name='check_current_attendees_non_negative'),
        CheckConstraint('current_attendees <= max_attendees', name='check_attendees_within_capacity')
    )
    
    @validates('title')
    def validate_title(self, key, title):
        if len(title.strip()) < 3:
            raise ValueError('Title must be at least 3 characters long')
        return title
    
    @validates('description')
    def validate_description(self, key, description):
        if len(description.strip()) < 10:
            raise ValueError('Description must be at least 10 characters long')
        return description
    
    @validates('max_attendees')
    def validate_max_attendees(self, key, max_attendees):
        if max_attendees < 1:
            raise ValueError('Maximum attendees must be at least 1')
        return max_attendees
    
    def is_full(self):
        return self.current_attendees >= self.max_attendees
    
    def can_register(self):
        return self.is_active and not self.is_full()
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'max_attendees': self.max_attendees,
            'current_attendees': self.current_attendees,
            'created_by': self.created_by,
            'university': self.university,
            'image': self.image,  # Include image in the response
            'tags': self.tags,  # Include tags in the response
            'is_active': self.is_active,
            'is_full': self.is_full(),
            'can_register': self.can_register(),
            'created_at': self.created_at.isoformat()
        }

# Event Attendee Model (for tracking event registrations)
class EventAttendee(db.Model):
    __tablename__ = 'event_attendees'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    registered_at = db.Column(db.DateTime, default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))
    attended = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='unique_event_attendee'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'registered_at': self.registered_at.isoformat(),
            'attended': self.attended
        }

# Comment Model
class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc), onupdate=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))

    # Relationships
    user = db.relationship('User', backref='comments', lazy=True)
    event = db.relationship('Event', backref='comments', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'user_name': f"{self.user.first_name} {self.user.last_name}" if self.user else None,
            'user_profile_picture': self.user.profile_picture if self.user else None,
            'user': self.user.to_dict() if self.user else None
        }

# Notification Model
class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'event_edited', 'event_cancelled', 'event_ended', 'new_comment'
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))

    # Relationships
    user = db.relationship('User', backref='notifications', lazy=True)
    event = db.relationship('Event', backref='notifications', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'event_id': self.event_id,
            'type': self.type,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'event_title': self.event.title if self.event else None
        }
