import cv2
import numpy as np
import importlib
import warnings
from collections import deque
import statistics
warnings.filterwarnings('ignore')

class FaceDetector:
    def __init__(self):
        # Optionally use DeepFace for more accurate emotion detection
        # (`deepface` package must be installed separately). Set to False by default.
        self.use_deepface = False
        self.deepface_available = self._check_deepface_available()

        # Delayed/guarded import of MediaPipe submodules to avoid pulling in
        # mediapipe.tasks (which can import TensorFlow) at top-level. This
        # prevents protobuf / tensorflow import conflicts from crashing the
        # whole app during module import.
        self.mp_face_mesh = None
        self.mp_face_detection = None
        self.drawing_utils = None
        self.face_mesh = None
        self.face_detector = None
        self.FACEMESH_TESSELATION = None

        try:
            # import internal mediapipe solutions modules directly to avoid
            # triggering mediapipe.tasks (which imports tensorflow)
            mp_face_mesh = importlib.import_module('mediapipe.python.solutions.face_mesh')
            mp_face_detection = importlib.import_module('mediapipe.python.solutions.face_detection')
            drawing_utils = importlib.import_module('mediapipe.python.solutions.drawing_utils')

            self.mp_face_mesh = mp_face_mesh
            self.mp_face_detection = mp_face_detection
            self.drawing_utils = drawing_utils

            self.face_mesh = mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )

            self.face_detector = mp_face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=0.5
            )

            self.FACEMESH_TESSELATION = mp_face_mesh.FACEMESH_TESSELATION
        except Exception as e:
            # Keep the detector in a safe, non-functional state and log the
            # error so the rest of the app can continue running.
            print(f" mediapipe import/init failed: {e}")

        # Temporal smoothing buffers and debounce for stable behavior
        # Use small windows to keep responsiveness while reducing jitter
        self.ear_history = deque(maxlen=5)
        self.mouth_ratio_history = deque(maxlen=5)
        self.neutrality_history = deque(maxlen=5)

        # Debounce state for expressions (require N frames of change)
        self.current_expression = 'neutral'
        self._expr_change_count = 0
        self._expr_required_frames = 3

    def _check_deepface_available(self):
        try:
            import deepface  # noqa: F401
            return True
        except Exception:
            return False
    
    def detect(self, frame):
        """Detect face using MediaPipe and return detection results or None"""
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if len(frame.shape) == 3 else frame
            results = self.face_detector.process(rgb_frame)
            
            if results.detections and len(results.detections) > 0:
                return results
            return None
        except Exception as e:
            print(f" Face detection error: {str(e)[:50]}")
            return None
    
    def _calculate_eye_aspect_ratio(self, landmarks, eye_indices):
        """Calculate Eye Aspect Ratio (EAR) for eye closure detection"""
        try:
            eye_points = np.array([landmarks[i] for i in eye_indices])
            
            vertical_1 = np.linalg.norm(eye_points[1] - eye_points[5])
            vertical_2 = np.linalg.norm(eye_points[2] - eye_points[4])
            horizontal = np.linalg.norm(eye_points[0] - eye_points[3])
            
            if horizontal == 0:
                return 0.0
            
            ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
            return ear
        except Exception as e:
            print(f"[v0] EAR calculation error: {str(e)[:30]}")
            return 0.0
    
    def detect_eye_closure(self, frame):
        """Detect eye closure using MediaPipe face mesh landmarks"""
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if len(frame.shape) == 3 else frame
            results = self.face_mesh.process(rgb_frame)
            
            if not results.multi_face_landmarks or len(results.multi_face_landmarks) == 0:
                # No landmarks: clear smoothing buffers to avoid stale values
                self.ear_history.clear()
                self.mouth_ratio_history.clear()
                return {'detected': False, 'avg_ear': 0.5}
            
            landmarks = results.multi_face_landmarks[0].landmark
            h, w = frame.shape[:2]

            landmarks_pixels = np.array([
                [int(landmark.x * w), int(landmark.y * h)] 
                for landmark in landmarks
            ])
            # store last landmarks for downstream heuristics (e.g., smile detection)
            self.last_landmarks_pixels = landmarks_pixels
            self.last_frame_size = (w, h)
            
            left_eye_indices = [33, 160, 158, 133, 153, 144]
            right_eye_indices = [362, 385, 387, 263, 373, 380]
            
            left_ear = self._calculate_eye_aspect_ratio(landmarks_pixels, left_eye_indices)
            right_ear = self._calculate_eye_aspect_ratio(landmarks_pixels, right_eye_indices)
            
            avg_ear = (left_ear + right_ear) / 2.0
            # Update smoothing buffer and compute smoothed EAR
            self.ear_history.append(avg_ear)
            try:
                smoothed_ear = float(statistics.mean(self.ear_history))
            except Exception:
                smoothed_ear = float(avg_ear)

            return {
                'detected': True,
                'left_ear': left_ear,
                'right_ear': right_ear,
                'avg_ear': avg_ear,
                'smoothed_ear': smoothed_ear
            }
        except Exception as e:
            print(f" Eye detection error: {str(e)[:50]}")
            return {'detected': False, 'avg_ear': 0.5}
    
    def extract_facial_features(self, frame, results, eye_data=None, eye_closure_threshold=0.15):
        """Extract facial features from detection results.

        If `self.use_deepface` is True and the `deepface` package is available,
        use DeepFace.analyze on the detected face ROI to get a more accurate
        `dominant_emotion` and emotion probabilities. Falls back to simple
        eye-aspect based eyes_closed and default 'neutral' expression.
        """
        features = {
            'neutrality': 1.0,
            'eye_aspect_ratio': eye_data.get('avg_ear', 0.5) if eye_data else 0.5,
            'eyes_closed': False,
            'expression': 'neutral',
            'dominant_emotion': 'neutral',
            'emotions': {
                'neutral': 1.0,
                'happy': 0.0,
                'sad': 0.0,
                'angry': 0.0,
                'surprise': 0.0,
                'fear': 0.0,
                'disgust': 0.0
            }
        }
        
        try:
            if eye_data and eye_data.get('detected'):
                avg_ear = eye_data.get('avg_ear', 0.5)
                features['eye_aspect_ratio'] = avg_ear
                features['eyes_closed'] = avg_ear < eye_closure_threshold

            # If DeepFace is enabled, try to analyze the face ROI for emotion
            if self.use_deepface and results is not None:
                if not self.deepface_available:
                    print("[v0] DeepFace is not installed; falling back to heuristic emotion detection.")
                    self.use_deepface = False
                else:
                    try:
                        # Import here to keep deepface optional
                        from deepface import DeepFace

                        # Get bounding box from MediaPipe detection if available
                        det = None
                        if hasattr(results, 'detections') and results.detections:
                            det = results.detections[0]

                        if det is not None:
                            bbox = det.location_data.relative_bounding_box
                            h, w = frame.shape[:2]
                            x = max(0, int(bbox.xmin * w))
                            y = max(0, int(bbox.ymin * h))
                            bw = int(bbox.width * w)
                            bh = int(bbox.height * h)

                            # Expand box slightly for better context
                            pad_x = int(bw * 0.1)
                            pad_y = int(bh * 0.1)
                            x1 = max(0, x - pad_x)
                            y1 = max(0, y - pad_y)
                            x2 = min(w, x + bw + pad_x)
                            y2 = min(h, y + bh + pad_y)

                            face_roi = frame[y1:y2, x1:x2].copy()

                            if face_roi.size != 0:
                                # DeepFace returns emotion probabilities and dominant_emotion
                                analysis = DeepFace.analyze(face_roi, actions=['emotion'], enforce_detection=False)
                                dom = analysis.get('dominant_emotion')
                                emotions = analysis.get('emotion', {})

                                # Normalize results
                                features['expression'] = str(dom).lower() if dom is not None else features['expression']
                                # Provide full emotion probabilities
                                try:
                                    normalized = {k.lower(): float(v) / 100.0 for k, v in emotions.items()}
                                    # Ensure keys exist for expected emotions
                                    for k in ['neutral','happy','sad','angry','surprise','fear','disgust']:
                                        features['emotions'][k] = normalized.get(k, 0.0)
                                    # set dominant emotion
                                    features['dominant_emotion'] = str(dom).lower() if dom is not None else features['dominant_emotion']
                                except Exception:
                                    pass
                                # Use neutral probability as neutrality score (0-1)
                                neutral_prob = emotions.get('neutral', 0)
                                try:
                                    features['neutrality'] = float(neutral_prob) / 100.0 if neutral_prob is not None else features['neutrality']
                                except Exception:
                                    features['neutrality'] = features.get('neutrality', 1.0)
                    except Exception as e:
                        # If DeepFace fails for any reason, fall back silently
                        print(f"[v0] DeepFace analysis failed: {str(e)[:80]}")

            # If DeepFace is not available or didn't detect, fall back to a simple smile heuristic
            # using stored face mesh landmarks (if available).
            if not self.use_deepface:
                try:
                    lm = getattr(self, 'last_landmarks_pixels', None)
                    if lm is not None and lm.shape[0] > 300:
                        # MediaPipe face mesh indices for mouth corners and lips
                        # outer left corner: 61, outer right corner: 291
                        # upper lip center: 13, lower lip center: 14
                        left_corner = lm[61]
                        right_corner = lm[291]
                        top_lip = lm[13]
                        bottom_lip = lm[14]

                        mouth_width = np.linalg.norm(right_corner - left_corner)
                        mouth_height = np.linalg.norm(bottom_lip - top_lip)

                        # Estimate face width from landmark bounding box to gate small faces/noise
                        xs = lm[:, 0]
                        face_width = float(xs.max() - xs.min()) if xs.size > 0 else 0.0

                        # Avoid division by zero
                        if mouth_height > 0:
                            mouth_ratio = mouth_width / mouth_height
                        else:
                            mouth_ratio = 0.0

                        # Gate out tiny faces or noisy mouth measurements
                        if face_width <= 0 or mouth_width < 0.05 * face_width:
                            # treat as no clear mouth movement
                            mouth_ratio = 0.0

                        # Update smoothing buffer for mouth ratio
                        self.mouth_ratio_history.append(mouth_ratio)
                        try:
                            smoothed_mouth = float(statistics.mean(self.mouth_ratio_history))
                        except Exception:
                            smoothed_mouth = float(mouth_ratio)

                        # Heuristic: a wide mouth relative to height indicates smile
                        # Use a slightly conservative threshold and rely on debounce for stability
                        smile_threshold = 2.2
                        if smoothed_mouth > smile_threshold:
                            candidate_expr = 'smile'
                            candidate_neutrality = min(features.get('neutrality', 1.0), 0.15)
                        else:
                            candidate_expr = 'neutral'
                            candidate_neutrality = features.get('neutrality', 1.0)

                        # Debounce expression changes: require consecutive frames
                        if candidate_expr != self.current_expression:
                            self._expr_change_count += 1
                            if self._expr_change_count >= self._expr_required_frames:
                                self.current_expression = candidate_expr
                                self._expr_change_count = 0
                        else:
                            self._expr_change_count = 0

                        features['expression'] = self.current_expression
                        features['dominant_emotion'] = 'happy' if self.current_expression == 'smile' else self.current_expression
                        features['mouth_ratio'] = mouth_ratio
                        features['smoothed_mouth_ratio'] = smoothed_mouth
                        features['neutrality'] = candidate_neutrality
                        # Heuristic emotion scoring (rough estimates)
                        # happy ~ smoothed mouth above threshold
                        happy_score = max(0.0, (smoothed_mouth - smile_threshold) / max(1.0, smoothed_mouth))

                        # surprise ~ large mouth opening relative to face height
                        face_h = float(np.max(self.last_landmarks_pixels[:,1]) - np.min(self.last_landmarks_pixels[:,1])) if getattr(self, 'last_landmarks_pixels', None) is not None else 1.0
                        surprise_score = 0.0
                        if face_h > 0:
                            surprise_score = max(0.0, min(1.0, (mouth_height / face_h) * 3.0 - 0.5))

                        # Eyebrow vs eye vertical distance - frown/anger vs raised brows
                        angry_score = 0.0
                        sad_score = 0.0
                        fear_score = 0.0
                        disgust_score = 0.0

                        try:
                            lm = self.last_landmarks_pixels
                            if lm is not None:
                                # eyebrow indices (approximate): left and right eyebrow groups
                                left_brow_idx = [70,63,105,66,107]
                                right_brow_idx = [336,296,334,293,300]
                                left_eye_idx = [33,160,158,133,153,144]
                                right_eye_idx = [362,385,387,263,373,380]

                                left_brow_y = np.mean([lm[i][1] for i in left_brow_idx if i < lm.shape[0]])
                                right_brow_y = np.mean([lm[i][1] for i in right_brow_idx if i < lm.shape[0]])
                                left_eye_y = np.mean([lm[i][1] for i in left_eye_idx if i < lm.shape[0]])
                                right_eye_y = np.mean([lm[i][1] for i in right_eye_idx if i < lm.shape[0]])

                                # smaller distance between brow and eye indicates frown/anger
                                left_brow_gap = left_eye_y - left_brow_y
                                right_brow_gap = right_eye_y - right_brow_y
                                brow_gap = np.mean([left_brow_gap, right_brow_gap])

                                # normalize by face height
                                norm_gap = brow_gap / (face_h if face_h>0 else 1.0)
                                # if brows are very close to eyes (small gap), increase anger score
                                angry_score = max(0.0, min(1.0, (0.05 - norm_gap) * 20.0))

                                # mouth corners relative to lip center - downward corners indicate sadness
                                left_corner = lm[61] if 61 < lm.shape[0] else None
                                right_corner = lm[291] if 291 < lm.shape[0] else None
                                top_lip = lm[13] if 13 < lm.shape[0] else None
                                if left_corner is not None and right_corner is not None and top_lip is not None:
                                    corner_mean_y = (left_corner[1] + right_corner[1]) / 2.0
                                    # if corners are lower (larger y) than top lip by some margin, sad score increases
                                    downward = (corner_mean_y - top_lip[1])
                                    sad_score = max(0.0, min(1.0, downward / (face_h if face_h>0 else 1.0) * 2.5))
                        except Exception:
                            pass

                        # Compose emotions dict and normalize
                        raw = {
                            'happy': happy_score,
                            'surprise': surprise_score,
                            'angry': angry_score,
                            'sad': sad_score,
                            'fear': fear_score,
                            'disgust': disgust_score
                        }

                        # neutral = remaining mass
                        total_pos = sum(raw.values())
                        neutral_score = max(0.0, 1.0 - total_pos)

                        features['emotions']['neutral'] = float(max(0.0, min(1.0, neutral_score)))
                        for k,v in raw.items():
                            features['emotions'][k] = float(max(0.0, min(1.0, v)))

                        # pick dominant - ensure happy is dominant when smiling
                        if self.current_expression == 'smile':
                            features['emotions']['happy'] = 0.8
                            features['emotions']['neutral'] = 0.2
                        else:
                            dom = max(features['emotions'].items(), key=lambda x: x[1])[0]
                            features['dominant_emotion'] = dom
                except Exception as e:
                    # Non-fatal; keep defaults
                    pass

        except Exception as e:
            print(f"[v0] Feature extraction error: {str(e)[:50]}")
        
        return features
    
    def draw_landmarks(self, frame, results=None):
        """Draw face detection box on frame"""
        # Draw face mesh landmarks (points + tesselation) similar to reference
        try:
            # Ensure we have an RGB frame for MediaPipe processing
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if len(frame.shape) == 3 else frame

            if self.face_mesh is None or self.drawing_utils is None or self.FACEMESH_TESSELATION is None:
                return frame

            mesh_results = self.face_mesh.process(rgb)
            if not mesh_results.multi_face_landmarks:
                return frame

            # Draw first face landmarks and tesselation
            landmarks = mesh_results.multi_face_landmarks[0]

            # Use MediaPipe drawing utilities for consistent mesh rendering
            self.drawing_utils.draw_landmarks(
                image=rgb,
                landmark_list=landmarks,
                connections=self.FACEMESH_TESSELATION,
                landmark_drawing_spec=self.drawing_utils.DrawingSpec(color=(0,230,200), thickness=1, circle_radius=2),
                connection_drawing_spec=self.drawing_utils.DrawingSpec(color=(0,230,200), thickness=1)
            )

            # Convert back to BGR for downstream usage/display
            bgr_out = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            return bgr_out
        except Exception as e:
            print(f"[v0] Drawing error: {str(e)[:50]}")
            return frame
