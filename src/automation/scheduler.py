"""
Message Scheduler - Handles scheduled and recurring messages
"""
import time
import threading
import schedule
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable

from src.models.database import Database
from src.api.service_manager import SMSServiceManager

class MessageScheduler:
    """Handles scheduling and automation of SMS messages"""
    
    def __init__(self, database: Database, service_manager: SMSServiceManager):
        """Initialize the message scheduler"""
        self.db = database
        self.service_manager = service_manager
        self.running = False
        self.scheduler_thread = None
        self.lock = threading.Lock()
        self.callbacks = {}
        
        # Initialize the scheduler
        self._initialize_scheduler()
    
    def _initialize_scheduler(self):
        """Initialize the scheduler with any existing scheduled messages"""
        # Schedule the check for due messages every minute
        schedule.every(1).minutes.do(self.check_due_messages)
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            return
            
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
    
    def stop(self):
        """Stop the scheduler thread"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1.0)
            self.scheduler_thread = None
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            with self.lock:
                schedule.run_pending()
            time.sleep(1)
    
    def check_due_messages(self):
        """Check for and send any due scheduled messages"""
        with self.lock:
            # Get all due messages from the database
            due_messages = self.db.get_due_scheduled_messages()
            
            for message in due_messages:
                self._process_scheduled_message(message)
    
    def _process_scheduled_message(self, message):
        """Process a single scheduled message"""
        try:
            # Check if the message object is valid
            if not message or not isinstance(message, dict):
                print(f"Invalid message object: {message}")
                return False
                
            # Check if message is already processed
            if message.get('status') != 'pending':
                return False
                
            # Get message details with validation
            try:
                message_id = message.get('id')
                recipient = message.get('recipient')
                message_text = message.get('message')
                service = message.get('service')
                scheduled_time_str = message.get('scheduled_time')
                
                if not message_id or not recipient or not message_text or not scheduled_time_str:
                    raise ValueError(f"Missing required message fields: message_id={message_id}, recipient={recipient}, message_text={message_text is not None}, scheduled_time={scheduled_time_str is not None}")
                    
                # Parse schedule time
                schedule_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
                recurrence = message.get('recurring')
                recurrence_data = message.get('recurring_interval')
            except (KeyError, ValueError, TypeError) as e:
                print(f"Invalid message data: {e}")
                # Mark message as failed due to data error
                if message_id:
                    self.db.update_scheduled_message_status(
                        message_id=message_id,
                        status='failed'
                    )
                return False
                
            # Send the message
            response = self.service_manager.send_sms(
                recipient=recipient,
                message=message_text,
                service_name=service
            )
            
            if response.success:
                # If it's a recurring message, update its next schedule time
                if recurrence:
                    self._update_recurring_message(message)
                else:
                    # For one-time messages, mark as sent
                    self.db.update_scheduled_message_status(
                        message_id=message_id,
                        status='sent'
                    )
                    
                # Trigger any callback for successful sending
                self._trigger_callback('message_sent', {
                    'message_id': message_id,
                    'recipient': recipient,
                    'status': 'sent'
                })
            else:
                # Mark as failed
                self.db.update_scheduled_message_status(
                    message_id=message_id,
                    status='failed'
                )
                
                # Trigger callback for failed sending
                self._trigger_callback('message_failed', {
                    'message_id': message_id,
                    'recipient': recipient,
                    'status': 'failed',
                    'error': response.error
                })
            
            return True
        except Exception as e:
            print(f"Error processing scheduled message: {e}")
            # Try to mark the message as failed if we can get the ID
            try:
                if message and isinstance(message, dict) and 'id' in message:
                    self.db.update_scheduled_message_status(
                        message_id=message['id'],
                        status='failed'
                    )
            except:
                pass  # Ignore errors in error handling
            return False
    
    def _update_recurring_message(self, message):
        """Update the next schedule time for a recurring message"""
        message_id = message['id']
        recurrence = message['recurring']
        schedule_time = datetime.strptime(message['scheduled_time'], '%Y-%m-%d %H:%M:%S')
        recurrence_data = message.get('recurring_interval')
        
        # Parse the recurrence data if it's a JSON string
        if recurrence_data and isinstance(recurrence_data, str):
            try:
                recurrence_data = json.loads(recurrence_data)
            except json.JSONDecodeError:
                recurrence_data = {}
        else:
            recurrence_data = {}
        
        # Calculate the next schedule time based on recurrence type
        next_schedule_time = None
        
        if recurrence == 'daily':
            next_schedule_time = schedule_time + timedelta(days=1)
            
        elif recurrence == 'weekly':
            next_schedule_time = schedule_time + timedelta(weeks=1)
            
        elif recurrence == 'monthly':
            # Get the same day next month, handling month length differences
            next_month = schedule_time.month + 1
            next_year = schedule_time.year
            
            if next_month > 12:
                next_month = 1
                next_year += 1
                
            # Get the same day, but handle month length differences
            try:
                next_schedule_time = schedule_time.replace(year=next_year, month=next_month)
            except ValueError:
                # If the day doesn't exist in the next month (e.g., Jan 31 -> Feb 28)
                # Use the last day of the next month
                if next_month == 2:
                    next_schedule_time = schedule_time.replace(
                        year=next_year, month=next_month, day=28)
                    if next_year % 4 == 0 and (next_year % 100 != 0 or next_year % 400 == 0):
                        next_schedule_time = schedule_time.replace(
                            year=next_year, month=next_month, day=29)
                else:
                    # For 30-day months when the original day was 31
                    next_schedule_time = schedule_time.replace(
                        year=next_year, month=next_month, day=30)
            
        elif recurrence == 'custom':
            # Custom recurrence based on days interval
            days_interval = recurrence_data.get('days_interval', 1)
            next_schedule_time = schedule_time + timedelta(days=days_interval)
            
        # Update the scheduled message with the new schedule time
        if next_schedule_time:
            # Format the datetime for SQLite
            next_schedule_str = next_schedule_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Reset the status to pending for the next occurrence
            self.db.update_scheduled_message(
                message_id=message_id,
                schedule_time=next_schedule_time,
                status='pending'
            )
            
            # Trigger callback for message rescheduled
            self._trigger_callback('message_rescheduled', {
                'message_id': message_id,
                'next_schedule': next_schedule_str
            })
    
    def schedule_message(self, recipient: str, message: str, schedule_time: datetime,
                         recurrence: Optional[str] = None, 
                         recurrence_data: Optional[Dict[str, Any]] = None,
                         service: Optional[str] = None) -> Optional[int]:
        """Schedule a new message for sending"""
        with self.lock:
            # Format the datetime for SQLite
            scheduled_time_str = schedule_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Save to the database
            message_id = self.db.save_scheduled_message(
                recipient=recipient,
                message=message,
                scheduled_time=scheduled_time_str,
                recurring=recurrence,
                recurring_interval=None,
                recurrence_data=recurrence_data,
                service=service
            )
            
            if message_id:
                # Trigger callback for message scheduled
                self._trigger_callback('message_scheduled', {
                    'message_id': message_id,
                    'recipient': recipient,
                    'scheduled_time': scheduled_time_str
                })
                
            return message_id
    
    def cancel_scheduled_message(self, message_id: int) -> bool:
        """Cancel a scheduled message"""
        with self.lock:
            success = self.db.delete_scheduled_message(message_id)
            
            if success:
                # Trigger callback for message cancelled
                self._trigger_callback('message_cancelled', {
                    'message_id': message_id
                })
                
            return success
    
    def update_scheduled_message(self, message_id: int, 
                                recipient: Optional[str] = None,
                                message: Optional[str] = None,
                                schedule_time: Optional[datetime] = None,
                                recurrence: Optional[str] = None,
                                recurrence_data: Optional[Dict[str, Any]] = None,
                                service: Optional[str] = None) -> bool:
        """Update an existing scheduled message"""
        with self.lock:
            # Get the current message
            scheduled_messages = self.db.get_scheduled_messages()
            current = None
            for msg in scheduled_messages:
                if msg['id'] == message_id:
                    current = msg
                    break
            
            if not current:
                return False
            
            # Convert recurrence_data to JSON if it's a dictionary
            recurring_interval = None
            if recurrence_data is not None:
                if isinstance(recurrence_data, dict):
                    recurring_interval = json.dumps(recurrence_data)
                else:
                    recurring_interval = recurrence_data
            
            # Update the message
            result = self.db.update_scheduled_message(
                message_id=message_id,
                recipient=recipient,
                message=message,
                scheduled_time=schedule_time,
                recurring=recurrence,
                recurring_interval=recurring_interval,
                service=service
            )
            
            # Trigger callback for message updated
            if result:
                self._trigger_callback('message_updated', {
                    'message_id': message_id
                })
                
            return result
    
    def get_scheduled_messages(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get scheduled messages with optional status filter"""
        with self.lock:
            messages = self.db.get_scheduled_messages()
            
            # Filter by status if requested
            if status:
                messages = [m for m in messages if m['status'] == status]
                
            # Parse recurrence data if it's a JSON string
            for message in messages:
                if 'recurring_interval' in message and message['recurring_interval']:
                    try:
                        message['recurring_interval'] = json.loads(message['recurring_interval'])
                    except json.JSONDecodeError:
                        pass
                        
            return messages
    
    def register_callback(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for scheduler events"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    def _trigger_callback(self, event_type: str, data: Dict[str, Any]):
        """Trigger registered callbacks for an event"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in scheduler callback: {e}") 