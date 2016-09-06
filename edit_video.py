import os
import sys
import json
import imutils
import numpy as np
import cv2

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

def get_cap_prop_fourcc(cap):
   """
   This function is not used. It's here for research value. Basically it cost me half a day and
   I can't bare to delete it.

   RESEARCH
   MP4's from my phone return a CAP_PROP_FOURCC of 828601953:
   
      828601953 --hex--> 31 63 76 61 --ascii--> 1cva --reversed--> avc1
   
   The mystery codec: AVC1
   
   Which isn't supported on Windows. Which is why 'XVID' is the default 'fourcc_text' and this function isn't used for now. 
   You'll probably have to change the config file for 'fourcc_text' depending on installed codecs for your 
   system.
   """
   original_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
   return original_fourcc

def draw_status(markup_frame, config, original_video_size, frame_counter, original_frame_count):
   sd = {
      'text_thickness': 1, 
      'margin_len': 60,
      'line_height': 20,
      'keystroke_color': (50, 255, 150),
      'info_color': (0, 0, 255),
      'font': cv2.FONT_HERSHEY_SIMPLEX,
      'line': cv2.LINE_AA,
      'scale': 0.5
      }
   draw_progress_bar(markup_frame, config, sd, frame_counter, original_frame_count)
   draw_ui_keys(markup_frame, config, sd, original_video_size)

def draw_progress_bar(frame, config, sd, frame_counter, original_frame_count):
   frame_width = frame.shape[1]
   pbar_len = frame_width - sd['margin_len'] * 2
   pbar_height = 8
   pbar_x1 = sd['margin_len']
   pbar_y1 = sd['margin_len']
   pbar_x2 = pbar_x1 + pbar_len
   pbar_y2 = pbar_y1 + pbar_height
   ind_height = pbar_height - 2
   ind_half_height = round(ind_height / 2)
   ind_x1 = pbar_x1 + 3
   ind_y1 = pbar_y1 + ind_half_height + 1
   ind_max_len = pbar_len - 5
   ind_len = round(ind_max_len * (frame_counter / original_frame_count))
   ind_x2 = ind_x1 + ind_len
   draw_text(frame, 'f (fewer) keeping 1 of every %d' % config['keep_frame_mod'], (ind_x1, ind_y1 - 8), sd) 
   draw_text(frame, 'v (more)     current frame #%d of %s' % (frame_counter, original_frame_count), (ind_x1, ind_y1 + ind_height + 11), sd)
   cv2.line(frame, (ind_x1, ind_y1), (ind_x2, ind_y1), (250, 200, 100), ind_height)
   keep_frame_total = int(original_frame_count / config['keep_frame_mod'])
   for i in range(keep_frame_total):
      tick_x1 = ind_x1 + int(ind_max_len * ((i + 1) / keep_frame_total))
      tick_y1 = ind_y1 + 2
      tick_y2 = ind_y1 + ind_half_height
      cv2.line(frame, (tick_x1, tick_y1), (tick_x1, tick_y2), sd['keystroke_color'], 1)
   cv2.rectangle(frame, (pbar_x1, pbar_y1), (pbar_x2, pbar_y2), sd['info_color'], 1)

def draw_text(frame, text, location, sd, color='keystroke_color'):
   cv2.putText(frame, text, location, 
               sd['font'], sd['scale'], sd[color], sd['text_thickness'], sd['line'])

def draw_ui_keys(frame, config, sd, original_video_size):
   # Crop-corner upper-left
   (text_x1, text_y1) = (config['crop_x1'] + 5, config['crop_y1'] + sd['line_height'])
   draw_text(frame, '%s' % str((config['crop_x1'],config['crop_y1'])), (text_x1, text_y1), sd, 'info_color')
   text_x1 += 10
   text_y1 += sd['line_height'] - 5
   draw_text(frame, '  w', (text_x1 - 3, text_y1), sd)
   text_y1 += sd['line_height'] - 5
   draw_text(frame, 'a s d', (text_x1, text_y1), sd)

   # Crop-corner lower-right
   (text_x1, text_y1) = (config['crop_x2'] - sd['margin_len'] * 3, config['crop_y2'] - 10)
   draw_text(frame, '%s' % str((config['crop_x2'],config['crop_y2'])), (text_x1, text_y1), sd, 'info_color')
   text_x1 += 15
   text_y1 -= sd['line_height'] - 2
   draw_text(frame, 'j k l', (text_x1, text_y1), sd)
   text_y1 -= sd['line_height'] - 5
   draw_text(frame, '  i', (text_x1 - 3, text_y1), sd)

   # Other keys
   text_x1 = sd['margin_len']
   text_y1 = sd['margin_len'] + sd['line_height'] * 3
   orig_to_new_size_text = r'%s -> %s' % (str((original_video_size)), str((config['crop_x2'] - config['crop_x1'], config['crop_y2'] - config['crop_y1'])))
   draw_text(frame, orig_to_new_size_text, (text_x1, text_y1), sd, 'info_color')
   text_y1 += sd['line_height']
   draw_text(frame, 'o (create video)', (text_x1, text_y1), sd)
   text_y1 += sd['line_height']
   draw_text(frame, 'z (save config)', (text_x1, text_y1), sd)
   text_y1 += sd['line_height']
   draw_text(frame, 'x (steady mode) %s' % config['steady_mode'], (text_x1, text_y1), sd)
   text_y1 += sd['line_height']
   draw_text(frame, 'q (quit)', (text_x1, text_y1), sd)

def get_user_input_while_looping(config):
   cap = None
   speed_up = True
   frames_at_this_rate = None
   try:
      base_dir, source_file = os.path.split(config['video_source'])

      cap = cv2.VideoCapture(config['video_source'])
      original_fps = cap.get(cv2.CAP_PROP_FPS)
      original_video_size = get_cap_prop_size(cap)
      original_format = cap.get(cv2.CAP_PROP_FORMAT)
      original_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

      """
      # Setting FPS has no effect in my environment
      cap.set(cv2.CAP_PROP_FPS, 5.0)
      print('CAP_PROP_FPS(%s)' % cap.get(cv2.CAP_PROP_FPS))
      """

      config['crop_x2'] = config.get('crop_x2', original_video_size[0])
      config['crop_y2'] = config.get('crop_y2', original_video_size[1])
      w = config['crop_x2'] - config['crop_x1']
      h = config['crop_y2'] - config['crop_y1']

      print('Processing movie width(%d) height(%d) in(%s) from:\n\t%s' % (original_video_size[0], original_video_size[1], base_dir, source_file))
      user_is_selecting_size = True
      anchor_gray_frame = None
      anchor_crop_points = None
      frame_counter = -1

      keeper_frame = None
      while user_is_selecting_size:
         (grabbed, current_frame) = cap.read()
         # if the frame could not be grabbed, then we have reached the end of the video
         if not grabbed:
            # Loop it
            cap.release()
            cap = cv2.VideoCapture(config['video_source'])
            frame_counter = -1
            continue

         frame_counter += 1
         is_keeper_frame = frame_counter % config['keep_frame_mod'] == 0
         if is_keeper_frame:
            # Perform analsys against a previous keeper_frame.
            keeper_frame = current_frame
            current_crop_points = (config['crop_x1'], config['crop_y1'], config['crop_x2'], config['crop_y2'])
            if config['steady_mode']:
               gray_frame = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
               if (anchor_gray_frame is None) or (not anchor_crop_points == current_crop_points):
                  anchor_gray_frame = gray_frame
                  anchor_gray_frame_float32 = np.float32(anchor_gray_frame)
                  anchor_crop_points = current_crop_points
               gray_frame_float32 = np.float32(gray_frame)
               (xshift, yshift), some_number = cv2.phaseCorrelate(anchor_gray_frame_float32, gray_frame_float32)
            else:
               xshift = 0
               yshift = 0
               if keeper_frame is None:
                  keeper_frame = current_frame

         if is_keeper_frame:
            if frames_at_this_rate == 0 or frames_at_this_rate is None:
               frames_at_this_rate = config['keep_frame_mod']
            frames_at_this_rate -= 1
            if frames_at_this_rate == 0:
               if speed_up:
                  if config['keep_frame_mod'] > config['keep_frame_mod_min']:
                     config['keep_frame_mod'] -= 1
                  else:
                     speed_up = not speed_up
               else:
                  if config['keep_frame_mod'] < config['keep_frame_mod_max']:
                     config['keep_frame_mod'] += 1
                  else:
                     speed_up = not speed_up

         # Clone the keeper_frame for markup. Leave keeper_frame untouched. Clone keeper_frame everytime to avoid getting messy, overlapping markup.
         markup_frame = cv2.copyMakeBorder(keeper_frame, 0,0,0,0, cv2.BORDER_REPLICATE)
         cv2.rectangle(markup_frame, (config['crop_x1'], config['crop_y1']), (config['crop_x2'], config['crop_y2']), (0, 0, 255), 1)
         if config['steady_mode']:
            (xshifted, yshifted, x2shifted, y2shifted) = (round(config['crop_x1'] + xshift), round(config['crop_y1'] + yshift), round(config['crop_x2'] + xshift), round(config['crop_y2'] + yshift))
            cv2.rectangle(markup_frame, (xshifted, yshifted), (x2shifted, y2shifted), (0, 255, 0), 1)

         draw_status(markup_frame, config, original_video_size, frame_counter, original_frame_count)

         show(True, markup_frame)
         key = cv2.waitKey(1) & 0xFF
         if key == ord('q'):
            # abort
            raise KeyboardInterrupt
         elif key == ord('a') and config['crop_x1'] > 0:
            config['crop_x1'] -= 1
         elif key == ord('d') and config['crop_x1'] < original_video_size[0]:
            config['crop_x1'] += 1
         elif key == ord('w') and config['crop_y1'] > 0:
            config['crop_y1'] -= 1
         elif key == ord('s') and config['crop_y1'] < original_video_size[1]:
            config['crop_y1'] += 1
         elif key == ord('j') and config['crop_x2'] > 1:
            config['crop_x2'] -= 1
         elif key == ord('l') and config['crop_x2'] < original_video_size[0]:
            config['crop_x2'] += 1
         elif key == ord('i') and config['crop_y2'] > 1:
            config['crop_y2'] -= 1
         elif key == ord('k') and config['crop_y2'] < original_video_size[1]:
            config['crop_y2'] += 1
         elif key == ord('o'):
            # move on to next step, writing the cropped video
            user_is_selecting_size = False
         elif key == ord('f'):
            config['keep_frame_mod'] += 1
         elif key == ord('x'):
            config['steady_mode'] = not config['steady_mode']
         elif key == ord('v') and config['keep_frame_mod'] > 1:
            config['keep_frame_mod'] -= 1
         elif key == ord('z'):
            save_config(config)
            print_config_file(config)

      return anchor_gray_frame
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

def write_video(config, anchor_gray_frame):
   video = None
   cap = None
   speed_up = True
   frames_at_this_rate = None
   try:
      base_dir, source_file = os.path.split(config['video_source'])
      cap = cv2.VideoCapture(config['video_source'])
      original_fps = cap.get(cv2.CAP_PROP_FPS)
      original_video_size = get_cap_prop_size(cap)
      original_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

      # Write the resulting movie
      target_file_base = r'xy%d-%d_%dx%d_mod%d_steady(%d)_%s_' % (config['crop_x1'], config['crop_y1'], config['crop_x2'], config['crop_y2'], config['keep_frame_mod'], config['steady_mode'], source_file)
      target_video_filename = r'%s.avi' % target_file_base 
      target_config_filename = r'%s\%s.json' % (base_dir, target_file_base)
      config['config_file_name'] = target_config_filename
      save_config(config)
      print('\t\tto\n\t%s' % target_video_filename)

      fourcc = cv2.VideoWriter_fourcc(*config['fourcc_text'])
      video = cv2.VideoWriter(r'%s\%s' % (base_dir, target_video_filename), fourcc, original_fps, (config['crop_x2'] - config['crop_x1'], config['crop_y2'] - config['crop_y1']), True)
      display_on = True
      frame_counter = -1
      anchor_gray_frame_float32 = np.float32(anchor_gray_frame)
      while True:
         (grabbed, original_frame) = cap.read()
         # if the frame could not be grabbed, then we have reached the end of the video
         if not grabbed:
            break

         frame_counter += 1
         if frame_counter % config['keep_frame_mod'] != 0:
            continue

         if frames_at_this_rate == 0 or frames_at_this_rate is None:
            frames_at_this_rate = config['keep_frame_mod']
         frames_at_this_rate -= 1
         if frames_at_this_rate == 0:
            if speed_up:
               if config['keep_frame_mod'] > config['keep_frame_mod_min']:
                  config['keep_frame_mod'] -= 1
               else:
                  speed_up = not speed_up
            else:
               if config['keep_frame_mod'] < config['keep_frame_mod_max']:
                  config['keep_frame_mod'] += 1
               else:
                  speed_up = not speed_up

         if config['steady_mode']:
            gray_frame = cv2.cvtColor(original_frame, cv2.COLOR_BGR2GRAY)
            gray_frame_float32 = np.float32(gray_frame)
            (xshift, yshift), some_number = cv2.phaseCorrelate(anchor_gray_frame_float32, gray_frame_float32)
            xs, ys, xs2, ys2 = round(config['crop_x1'] + xshift), round(config['crop_y1'] + yshift), round(config['crop_x2'] + xshift), round(config['crop_y2'] + yshift)
         else:
            xs, ys, xs2, ys2 = config['crop_x1'], config['crop_y1'], config['crop_x2'], config['crop_y2']

         new_frame = original_frame[ys:ys2, xs:xs2, :]
         video.write(new_frame)

         # new_frame has been written to disk. Now we can deface new_frame for user feedback.
         draw_status(new_frame, config, original_video_size, frame_counter, original_frame_count)
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
         print('Releasing video target: %s' % (target_video_filename))
         video.release()
      print('Destroying any OpenCV')
      cv2.destroyAllWindows()

def edit_movie(config):
   anchor_gray_frame = get_user_input_while_looping(config)
   write_video(config, anchor_gray_frame)

def print_config_file(config):
   print('Config file located at:\n\t%s\nPoint "video_source" path to your video. Use fully qualified path or relative path. Current working directory:\n\t%s' \
      % (config['config_file_name'], os.getcwd()))
   print('Current config contents:')
   with open(config['config_file_name'], 'r') as f:
      for line in f:
         print(line)

def save_config(config):
   with open(config['config_file_name'], 'w') as f:
      json.dump(config, f)

def normalize_config(config):
   config['config_file_name'] = config.get('config_file_name', r'edit_video_config.json')
   config['video_source'] = config.get('video_source', 'your_video.mp4')
   config['keep_frame_mod'] = config.get('keep_frame_mod', 1)
   config['keep_frame_mod_min'] = config.get('keep_frame_mod_min', config['keep_frame_mod'])
   config['keep_frame_mod_max'] = config.get('keep_frame_mod_max', config['keep_frame_mod'])
   config['steady_mode'] = config.get('steady_mode', False)
   config['crop_x1'] = config.get('crop_x1', 0)
   config['crop_y1'] = config.get('crop_y1', 0)
   config['crop_x2'] = config.get('crop_x2', 1920)
   config['crop_y2'] = config.get('crop_y2', 1080)
   config['fourcc_text'] = config.get('fourcc_text', 'XVID')

def create_default_config(config_file_name):
   config = {'config_file_name':config_file_name}
   normalize_config(config)
   save_config(config)
   print('New config file created.')
   print_config_file(config)

def load_config(config_file_name):
   with open(config_file_name, 'r') as f:
      config = json.load(f)
   config['config_file_name'] = config_file_name
   return config

def main():
   config_file_name = r'edit_video_config.json'
   # Command line config takes precedence if one is found
   if len(sys.argv) > 1:
      if os.path.isfile(sys.argv[1]):
         ext = os.path.splitext(sys.argv[1])[1]
         if ext == '.json':
            config_file_name = os.path.normpath(sys.argv[1])

   try:
      config = load_config(config_file_name)
      if not os.path.isfile(config['video_source']):
         print('video_source is not a file:\n\t%s' % config['video_source'])
         print_config_file(config)
         return 1
      normalize_config(config)
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
