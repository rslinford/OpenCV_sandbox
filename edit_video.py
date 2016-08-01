import os
import json
import imutils
import cv2

def ensure_a_window(display_on, frame):
   show(display_on, frame)

def toggle_display(display_on, frame):
   cv2.destroyAllWindows()
   ensure_a_window(display_on, frame)
   return not display_on

def show(display_on, original_frame):
   if display_on:
      cv2.imshow('Video', original_frame)

def get_cap_prop_size(cap):
   return (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

def get_user_input(video_source):
   cap = None
   try:
      base_dir, source_file = os.path.split(video_source)

      cap = cv2.VideoCapture(video_source)
      original_fps = cap.get(cv2.CAP_PROP_FPS)
      original_video_size = get_cap_prop_size(cap)
      (x, y) = (0, 0)
      (w, h) = (original_video_size[0], original_video_size[1])
      keep_frame_mod = 1
      frame_counter = -1

      print('Processing movie width(%d) height(%d) in(%s) from:\n\t%s' % (original_video_size[0], original_video_size[1], base_dir, source_file))

      user_is_selecting_size = True
      while user_is_selecting_size:
         (grabbed, original_frame) = cap.read()
         # if the frame could not be grabbed, then we have reached the end of the video
         if not grabbed:
            # Loop it
            cap.release()
            cap = cv2.VideoCapture(video_source)
            frame_counter = -1
            continue

         frame_counter += 1
         if frame_counter % keep_frame_mod != 0:
            continue

         cv2.rectangle(original_frame, (x, y), (x+w, y+h), (0, 0, 255), 1)
         status_text = r'Original %s -> %s at %s Frame 1/%d' % (str((original_video_size)), str((w,h)), str((x,y)), keep_frame_mod)
         text_color = (0, 0, 255)
         text_thickness = 1
         cv2.putText(original_frame, status_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, text_thickness)
         show(True, original_frame)
 
         key = cv2.waitKey(1) & 0xFF
         if key == ord('q'):
            # abort
            raise KeyboardInterrupt
         elif key == ord('a') and x > 0:
            x -= 1
         elif key == ord('d') and x < original_video_size[0]:
            x += 1
         elif key == ord('w') and y > 0:
            y -= 1
         elif key == ord('s') and y < original_video_size[1]:
            y += 1
         elif key == ord('j') and w > 1:
            w -= 1
         elif key == ord('l') and w < original_video_size[0]:
            w += 1
         elif key == ord('i') and h > 1:
            h -= 1
         elif key == ord('k') and h < original_video_size[1]:
            h += 1
         elif key == ord('o'):
            # move on to next step, writing the clipped video
            user_is_selecting_size = False
         elif key == ord('f'):
            keep_frame_mod += 1
         elif key == ord('v') and keep_frame_mod > 1:
            keep_frame_mod -= 1

      return (x,y,w,h,keep_frame_mod)
   except (KeyboardInterrupt):
      print('Program ending per user reqeust.')
      raise
   except (SystemExit):
      print('System exit signaled. Attempting to clean resources.')
      raise
   finally:
      if cap:
         print('Releasing video source: %s' % (source_file))
         cap.release()
      print('Destroying any OpenCV')
      cv2.destroyAllWindows()

def save_result(video_source, x,y, w,h, keep_frame_mod):
   video = None
   cap = None
   try:
      base_dir, source_file = os.path.split(video_source)

      cap = cv2.VideoCapture(video_source)
      original_fps = cap.get(cv2.CAP_PROP_FPS)
      original_video_size = get_cap_prop_size(cap)
      frame_counter = -1

      # Write the resulting movie
      target_file = r'xy%d-%d_%dx%d_mod%d_%s_.avi' % (x, y, w, h, keep_frame_mod, source_file)
      print('\t\tto\n\t%s' % target_file)

      fourcc = cv2.VideoWriter_fourcc(*'XVID')
      video = cv2.VideoWriter(r'%s\%s' % (base_dir, target_file), fourcc, original_fps, (w,h), True)
      display_on = True
      frame_counter = -1
      while True:
         (grabbed, original_frame) = cap.read()
         # if the frame could not be grabbed, then we have reached the end of the video
         if not grabbed:
            break

         frame_counter += 1
         if frame_counter % keep_frame_mod != 0:
            continue

         y2 = y + h
         x2 = x + w
         new_frame = original_frame[y:y2, x:x2, :]

         video.write(new_frame)
         show(display_on, new_frame)
 
         key = cv2.waitKey(1) & 0xFF
         if key == ord('q'):
            raise KeyboardInterrupt
         elif key == ord('p'):
            display_on = toggle_display(display_on, new_frame)

   except (KeyboardInterrupt):
      print('Program ending per user reqeust.')
      raise
   except (SystemExit):
      print('System exit signaled. Attempting to clean resources.')
      raise
   finally:
      if cap:
         print('Releasing video source: %s' % (source_file))
         cap.release()
      if video:
         print('Releasing video target: %s' % (target_file))
         video.release()
      print('Destroying any OpenCV')
      cv2.destroyAllWindows()

def edit_movie(video_source):
   (x, y, w, h, keep_frame_mod) = get_user_input(video_source)
   save_result(video_source, x, y, w, h, keep_frame_mod)

def show_config(config_file_name):
   print('Please edit config file:\n\t%s\nPoint source to your video. Use fully qualified path or relative to the current working directory:\n\t%s' \
      % (config_file_name, os.getcwd()))
   print('Current config contents:')
   with open(config_file_name, 'r') as f:
      for line in f:
         print(line)

def create_default_config(config_file_name):
   config = {'video_source':'your_video.mp4'}
   with open(config_file_name, 'w') as f:
      json.dump(config, f)
   print('New config file created.')
   show_config(config_file_nam   e)

"""
Testing 
"""
def main():
   config_file_name = r'edit_video_config.json'
   try:
      with open(config_file_name, 'r') as f:
         config = json.load(f)
      video_source = config['video_source']
      if not os.path.isfile(video_source):
         show_config(config_file_name)
         return 1
      edit_movie(video_source)
   except (FileNotFoundError):
      create_default_config(config_file_name)

if __name__ == '__main__':
   try:
      main()
      print('\n[Normal Exit]')
   except (KeyboardInterrupt):
      print('\n[User Exit]')
   except (SystemExit):
      print('\n[System Exit]')
