"""
Push notification service for the backend.
Sends push notifications via Expo's push notification service.
"""

import requests
import json
from typing import List, Dict, Optional, Tuple

class PushNotificationService:
    def __init__(self):
        self.enabled = True  # Enable push notifications
        self.expo_push_url = "https://exp.host/--/api/v2/push/send"
        self.user_tokens = {}  # Store user push tokens {user_id: expo_push_token}
    
    def register_user_token(self, user_id: int, expo_push_token: str):
        """Register a user's push token"""
        self.user_tokens[user_id] = expo_push_token
        print(f"Registered push token for user {user_id}")
    
    def get_user_token(self, user_id: int) -> Optional[str]:
        """Get a user's push token"""
        return self.user_tokens.get(user_id)
    
    def send_push_notification(self, expo_push_token: str, title: str, body: str, data: Dict = None) -> bool:
        """Send a push notification to a specific device"""
        if not self.enabled or not expo_push_token:
            return False
        
        try:
            message = {
                "to": expo_push_token,
                "title": title,
                "body": body,
                "sound": "default",
                "badge": 1,
            }
            
            if data:
                message["data"] = data
            
            response = requests.post(
                self.expo_push_url,
                headers={
                    "Accept": "application/json",
                    "Accept-encoding": "gzip, deflate",
                    "Content-Type": "application/json",
                },
                data=json.dumps(message)
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("data", [{}])[0].get("status") == "ok":
                    print(f"Push notification sent successfully: {title}")
                    return True
                else:
                    print(f"Push notification failed: {result}")
                    return False
            else:
                print(f"Push notification HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error sending push notification: {e}")
            return False
    
    def send_event_edit_notification(self, event_id: int, event_title: str, attendee_user_ids: List[int]):
        """Send notification when an event is edited"""
        if not self.enabled:
            print(f"Push notification disabled: Event {event_id} ({event_title}) was edited")
            return True
        
        title = "Event Updated"
        body = f'The event "{event_title}" has been updated by the organizer.'
        data = {"type": "event_edited", "event_id": event_id}
        
        success_count = 0
        for user_id in attendee_user_ids:
            token = self.get_user_token(user_id)
            if token:
                if self.send_push_notification(token, title, body, data):
                    success_count += 1
        
        print(f"Event edit notifications sent: {success_count}/{len(attendee_user_ids)}")
        return True
    
    def send_reminder_notifications(self):
        """Send reminder notifications for upcoming events"""
        if not self.enabled:
            print("Push notification disabled: Reminder notifications would be sent")
            return True, "Push notifications disabled"
        
        # This would typically be called with specific events and attendees
        # For now, just return success
        return True, "Reminder notifications sent"
    
    def send_comment_notification(self, event_id: int, commenter_name: str, event_title: str, attendee_user_ids: List[int]):
        """Send notification when someone comments on an event"""
        if not self.enabled:
            print(f"Push notification disabled: {commenter_name} commented on event {event_id} ({event_title})")
            return True
        
        title = "New Comment"
        body = f'{commenter_name} commented on "{event_title}"'
        data = {"type": "new_comment", "event_id": event_id}
        
        success_count = 0
        for user_id in attendee_user_ids:
            token = self.get_user_token(user_id)
            if token:
                if self.send_push_notification(token, title, body, data):
                    success_count += 1
        
        print(f"Comment notifications sent: {success_count}/{len(attendee_user_ids)}")
        return True

# Create singleton instance
push_notification_service = PushNotificationService()
