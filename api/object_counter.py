import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict
import time
           
def calculate(x, y, x1, y1, x2, y2):
    return (x-x1)*(y2-y1) - (y-y1)*(x2-x1)

class LiveObjectCounter:
    def __init__(self, model_path='yolo11n.pt', confidence_threshold=0.5, line_p1=(0, 0), line_p2=(0, 0)):
        """
        Initialize the live object counter
        
        Args:
            model_path: Path to YOLOv11 model (will download if not exists)
            confidence_threshold: Minimum confidence for detections
        """
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.class_names = self.model.names
        self.colors = self._generate_colors()
        self.hist = {}
        self.object_in = 0
        self.object_out = 0
        self.counted = set()
        self.line_p1 = line_p1
        self.line_p2 = line_p2
        
    def _generate_colors(self):
        """Generate random colors for each class"""
        np.random.seed(42)
        return {i: tuple(map(int, np.random.randint(0, 255, 3))) 
                for i in range(len(self.class_names))}
    
    def process_frame(self, frame):
        """
        Process a single frame and return annotated frame with counts
        
        Args:
            frame: Input frame from camera
            
        Returns:
            annotated_frame: Frame with bounding boxes and labels
            object_counts: Dictionary with object counts
        """
        # Run YOLOv11 inference
        results = self.model.track(frame, persist=True, conf=self.confidence_threshold, verbose=False)
        
        # Initialize object counts
        object_counts = defaultdict(int)
        
        # Process detections
        annotated_frame = frame.copy()
        
        if results[0].boxes is not None:
            #print(results[0].boxes)
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.int().cpu().numpy()#.tolist() if results[0].boxes.id is not None else [-1]*len(boxes)
            #print('ids:::',track_ids, 'boxes::', boxes)
            for box, conf, class_id, track_id in zip(boxes, confidences, class_ids, track_ids):
                if conf >= self.confidence_threshold:
                    # Get class name and increment count
                    class_name = self.class_names[class_id]
                    object_counts[class_name] += 1
                    
                    # Draw bounding box
                    x1, y1, x2, y2 = map(int, box)
                    cx=(x1+x2)//2
                    cy=(y1+y2)//2
                    if track_id in self.hist and track_id not in self.counted:
                        prev_cx, prev_cy=self.hist[track_id]
                        side_1=calculate(prev_cx, prev_cy, *self.line_p1, *self.line_p2)
                        side_2=calculate(cx, cy, *self.line_p1, *self.line_p2)
                        if side_1*side_2<0:
                            if side_2<0:
                                self.object_in +=1
                                cv2.circle(annotated_frame, (cx, cy), 15, color=(0,255,0),thickness= -1)
                            else:
                                self.object_out +=1
                                cv2.rectangle(annotated_frame, (cx, cy), 15, color=(0,0,255),thickness= -1)
                            self.counted.add(track_id)

                    self.hist[track_id]=(cx, cy)
                    color = self.colors[class_id]
                    
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Draw label with confidence
                    label = f"{class_name}-{track_id}: {conf:.2f}"
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                    
                    cv2.line(annotated_frame, self.line_p1, self.line_p2, color=(0, 255, 255), thickness=2)
                    cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                                (x1 + label_size[0], y1), color, -1)
                    cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return annotated_frame, dict(object_counts)
    
    def draw_counts_panel(self, frame, object_counts, fps=0):
        """
        Draw object counts panel on the frame
        
        Args:
            frame: Input frame
            object_counts: Dictionary with object counts
            fps: Current FPS
            
        Returns:
            frame: Frame with counts panel
        """
        # Create semi-transparent overlay
        overlay = frame.copy()
        
        panel_height = max(200, len(object_counts) * 30 + 100)
        cv2.rectangle(overlay, (10, 10), (350, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Title
        cv2.putText(frame, "Live Object Counter", (20, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # FPS
        cv2.putText(frame, f"FPS: {fps:.1f}", (20, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Total objects
        total_objects = sum(object_counts.values())
        cv2.putText(frame, f"Total Objects: {self.object_in} - {self.object_out}", (20, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Individual counts
        y_offset = 130
        for class_name, count in sorted(object_counts.items()):
            if count > 0:
                text = f"{class_name}: {count}"
                cv2.putText(frame, text, (20, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                y_offset += 25
        
        # Instructions
        cv2.putText(frame, "Press 'q' to quit, 's' to save", (20, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def run_live_counting(self, camera_index=0, save_video=False):
        """
        Run live object counting from camera
        
        Args:
            camera_index: Camera index (0 for default camera)
            save_video: Whether to save the output video
        """
        
        # Initialize camera
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print(f"Error: Could not open camera {camera_index}")
            return
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Video writer setup
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = None
        if save_video:
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out = cv2.VideoWriter('object_counting_output.avi', fourcc, fps, (width, height))
        
        # FPS calculation
        fps_counter = 0
        fps_timer = time.time()
        current_fps = 0
        
        print("Starting live object counting...")
        print("Press 'q' to quit, 's' to save current frame")
        xp=0
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame")
                break
            xp +=1
            if xp % 3 !=0:
                continue
            
            # Process frame
            start_time = time.time()
            annotated_frame, object_counts = self.process_frame(frame)
            
            # Calculate FPS
            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                current_fps = fps_counter
                fps_counter = 0
                fps_timer = time.time()
            
            # Draw counts panel
            final_frame = self.draw_counts_panel(annotated_frame, object_counts, current_fps)
            
            # Display frame
            cv2.imshow('Live Object Counter', final_frame)
            
            # Save video frame
            if save_video and out is not None:
                out.write(final_frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save current frame
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f'object_count_{timestamp}.jpg'
                cv2.imwrite(filename, final_frame)
                print(f"Frame saved as {filename}")
            
            # Print counts (optional)
            if object_counts:
                total = sum(object_counts.values())
                print(f"\rTotal objects: {total} | " + 
                      " | ".join([f"{k}: {v}" for k, v in object_counts.items()]), 
                      end="", flush=True)
        
        # Cleanup
        cap.release()
        if out is not None:
            out.release()
        cv2.destroyAllWindows()
        print("\nObject counting stopped.")

def main():
    """Main function to run the live object counter"""
    try:
        # Initialize counter with YOLOv11 nano model (fastest)
        counter = LiveObjectCounter(
            model_path='yolo11n.pt',  # You can use yolo11s.pt, yolo11m.pt, yolo11l.pt, yolo11x.pt for better accuracy
            confidence_threshold=0.5,
            line_p1=(450, 600),
            line_p2=(1250, 540)
        )
        
        # Run live counting
        counter.run_live_counting(
            camera_index='vm.mp4',     # Change if you have multiple cameras
            save_video=False    # Set to True to save video output
        )
        print("Object In: ", counter.object_in)
        print("Object In: ", counter.object_out)
        #print("history: ", counter.hist)
        
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()