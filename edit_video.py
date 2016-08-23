import os
import json
import imutils
import numpy as np
import cv2

config_file_name = r'edit_video_config.json'

def ensure_a_window(display_on, frame):
   show(display_on, frame)

def toggle_display(display_on, frame):
   cv2.destroyAllWindows()
   ensure_a_window(display_on, frame)
   return not display_on

def show(display_on, original_frame, title='Video'):
   if display_on:
      cv2.imshow(title, original_frame)

def get_cap_prop_size(cap):
   return (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

def get_user_input(config):
   cap = None
   steady_the_cam = False
   try:
      video_source = config['video_source']
      base_dir, source_file = os.path.split(video_source)
      cap = cv2.VideoCapture(video_source)

      #
      # MP4's from my phone return a CAP_PROP_FOURCC of 828601953:
      #
      #    828601953 --hex--> 31 63 76 61 --ascii--> 1cva --reversed--> avc1
      #
      # The mystery codec: AVC1
      #
      # Which isn't supported on Windows. Which is why XVID is hard coded further below. You'll probably have
      # to change it to work on you system depending on installed codecs.
      #
      original_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))

      original_fps = cap.get(cv2.CAP_PROP_FPS)
      original_video_size = get_cap_prop_size(cap)

      original_format = cap.get(cv2.CAP_PROP_FORMAT)
      original_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

      (x, y, x2, y2) = config.get('crop_points', (0,0,original_video_size[0], original_video_size[1]))
      w = x2 - x
      h = y2 - y
      keep_frame_mod = 1
      frame_counter = -1

      print('Processing movie width(%d) height(%d) in(%s) from:\n\t%s' % (original_video_size[0], original_video_size[1], base_dir, source_file))

      user_is_selecting_size = True

      anchor_gray_frame = None
      anchor_crop_points = None

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

         current_crop_points = (x, y, x2, y2)

         if steady_the_cam:
            gray_frame = cv2.cvtColor(original_frame, cv2.COLOR_BGR2GRAY)
            if (anchor_gray_frame is None) or (not anchor_crop_points == current_crop_points):
               anchor_gray_frame = gray_frame
               anchor_gray_frame_float32 = np.float32(anchor_gray_frame)
               anchor_crop_points = current_crop_points

            gray_frame_float32 = np.float32(gray_frame)
            (xshift, yshift), some_number = cv2.phaseCorrelate(anchor_gray_frame_float32, gray_frame_float32)
         else:
            xshift = 0
            yshift = 0

         # Draw on the original frame. It's "defaced" after this so no more analysis.

         cv2.rectangle(original_frame, (x, y), (x2, y2), (0, 0, 255), 1)
         if steady_the_cam:
            (xshifted, yshifted, x2shifted, y2shifted) = (round(x+xshift), round(y+yshift), round(x2+xshift), round(y2+yshift))
            cv2.rectangle(original_frame, (xshifted, yshifted), (x2shifted, y2shifted), (0, 255, 0), 1)

         status_text = r'Original %s -> %s at %s Steady(%d) Keep 1/%d Frame %d of %s' % (str((original_video_size)), str((x2-x,y2-y)), str((x,y)), steady_the_cam, keep_frame_mod, frame_counter, original_frame_count)
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
         elif key == ord('j') and x2 > 1:
            x2 -= 1
         elif key == ord('l') and x2 < original_video_size[0]:
            x2 += 1
         elif key == ord('i') and y2 > 1:
            y2 -= 1
         elif key == ord('k') and y2 < original_video_size[1]:
            y2 += 1
         elif key == ord('o'):
            # move on to next step, writing the clipped video
            user_is_selecting_size = False
         elif key == ord('f'):
            keep_frame_mod += 1
         elif key == ord('x'):
            steady_the_cam = not steady_the_cam
         elif key == ord('v') and keep_frame_mod > 1:
            keep_frame_mod -= 1
         elif key == ord('z'):
            save_config_crop_points(current_crop_points)

      return (x,y,x2,y2,keep_frame_mod, steady_the_cam, anchor_gray_frame)
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

def save_result(config, x,y, x2,y2, keep_frame_mod, steady_the_cam, anchor_gray_frame):
   video = None
   cap = None
   try:
      video_source = config['video_source']
      base_dir, source_file = os.path.split(video_source)

      cap = cv2.VideoCapture(video_source)
      original_fps = cap.get(cv2.CAP_PROP_FPS)
      original_video_size = get_cap_prop_size(cap)
      frame_counter = -1

      # Write the resulting movie
      target_file = r'xy%d-%d_%dx%d_mod%d_steady(%d)_%s_.avi' % (x, y, x2, y2, keep_frame_mod, steady_the_cam, source_file)
      print('\t\tto\n\t%s' % target_file)

      fourcc = cv2.VideoWriter_fourcc(*'XVID')
      video = cv2.VideoWriter(r'%s\%s' % (base_dir, target_file), fourcc, original_fps, (x2-x, y2-y), True)
      display_on = True
      frame_counter = -1
      anchor_gray_frame_float32 = np.float32(anchor_gray_frame)
      while True:
         (grabbed, original_frame) = cap.read()
         # if the frame could not be grabbed, then we have reached the end of the video
         if not grabbed:
            break

         frame_counter += 1
         if frame_counter % keep_frame_mod != 0:
            continue

         if steady_the_cam:
            gray_frame = cv2.cvtColor(original_frame, cv2.COLOR_BGR2GRAY)
            gray_frame_float32 = np.float32(gray_frame)
            (xshift, yshift), some_number = cv2.phaseCorrelate(anchor_gray_frame_float32, gray_frame_float32)
            xs, ys, xs2, ys2 = round(x+xshift), round(y+yshift), round(x2+xshift), round(y2+yshift)
         else:
            xs, ys, xs2, ys2 = x, y, x2, y2

         new_frame = original_frame[ys:ys2, xs:xs2, :]

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

def edit_movie(config):
   (x, y, w, h, keep_frame_mod, steady_the_cam, anchor_gray_frame) = get_user_input(config)
   save_result(config, x, y, w, h, keep_frame_mod, steady_the_cam, anchor_gray_frame)

def print_config_file():
   print('Please edit config file:\n\t%s\nPoint source to your video. Use fully qualified path or relative to the current working directory:\n\t%s' \
      % (config_file_name, os.getcwd()))
   print('Current config contents:')
   with open(config_file_name, 'r') as f:
      for line in f:
         print(line)

def save_config(config):
   with open(config_file_name, 'w') as f:
      json.dump(config, f)

def save_config_crop_points(crop_points):
   config = load_config()
   config['crop_points'] = crop_points
   save_config(config)

def create_default_config():
   config = {'video_source':'your_video.mp4'}
   save_config(config)
   print('New config file created.')
   print_config_file()

def load_config():
   with open(config_file_name, 'r') as f:
      config = json.load(f)
   return config

def main():
   try:
      config = load_config()
      video_source = config['video_source']
      if not os.path.isfile(video_source):
         print_config_file()
         return 1
      edit_movie(config)
   except (FileNotFoundError):
      create_default_config()

if __name__ == '__main__':
   try:
      main()
      print('\n[Normal Exit]')
   except (KeyboardInterrupt):
      print('\n[User Exit]')
   except (SystemExit):
      print('\n[System Exit]')
