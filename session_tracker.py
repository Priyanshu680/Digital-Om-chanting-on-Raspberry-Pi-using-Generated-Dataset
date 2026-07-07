import json
from datetime import datetime
from pathlib import Path

class SessionTracker:
    def __init__(self):
        self.session_start = None
        self.frames = []
        self.data_path = Path(__file__).parent.parent / "data"
        self.data_path.mkdir(exist_ok=True)
        
        self.last_eyes_closed_state = None
        self.last_audio_state = None
    
    def start_session(self):
        """Start a new meditation session"""
        self.session_start = datetime.now()
        self.frames = []
        self.last_eyes_closed_state = None
        self.last_audio_state = None
    
    def add_frame(self, neutrality_score, eyes_closed, audio_playing, expression="neutral"):
        """Add frame data"""
        # Ensure a session has been started to avoid TypeError when computing timestamp
        if self.session_start is None:
            # If no explicit session start, initialize it now so timestamps are valid
            self.session_start = datetime.now()
        # Normalize types to native Python types so JSON serialization works
        ts = float((datetime.now() - self.session_start).total_seconds())
        try:
            neutrality_val = float(neutrality_score) if neutrality_score is not None else 0.0
        except Exception:
            neutrality_val = 0.0

        eyes_closed_val = bool(eyes_closed)
        audio_playing_val = bool(audio_playing)
        expression_val = str(expression) if expression is not None else "neutral"

        self.frames.append({
            'timestamp': ts,
            'neutrality': neutrality_val,
            'eyes_closed': eyes_closed_val,
            'audio_playing': audio_playing_val,
            'expression': expression_val
        })
    
    def end_session(self):
        """Save session data"""
        if not self.session_start:
            return
        
        session_data = {
            'start_time': self.session_start.isoformat(),
            'duration': (datetime.now() - self.session_start).total_seconds(),
            'frames': self.frames,
            'metrics': self.get_session_metrics()
        }
        
        filename = self.data_path / f"session_{self.session_start.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print(f"[v0] Session saved: {filename}")
    
    def get_session_metrics(self):
        """Calculate current session metrics"""
        if not self.frames:
            return {
                'total_frames': 0,
                'eyes_closed_count': 0,
                'audio_playing_time': 0.0,
                'avg_neutrality': 0.0
            }
        
        total_frames = len(self.frames)
        eyes_closed_count = sum(1 for f in self.frames if f.get('eyes_closed', False))
        audio_playing_count = sum(1 for f in self.frames if f.get('audio_playing', False))
        avg_neutrality = sum(f.get('neutrality', 0) for f in self.frames) / total_frames if total_frames > 0 else 0
        
        return {
            'total_frames': total_frames,
            'eyes_closed_count': eyes_closed_count,
            'audio_playing_time': audio_playing_count,
            'avg_neutrality': avg_neutrality
        }
    
    def reset(self):
        """Reset current session"""
        self.session_start = None
        self.frames = []
