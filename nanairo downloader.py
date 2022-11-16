import os, re, json
import requests
from PIL import Image, ImageChops
## Using xml.etree.ElementTree might be better but rescinded due to vulnerabilities issue 

def is_greyscale(im):
    """
    Check if image is monochrome (1 channel or 3 identical channels).
    Takes Pillow image object.
    Returns True or False or ValueError exception.
    """
    if im.mode not in ("L", "RGB"):
        raise ValueError("Unsuported image mode")

    if im.mode == "RGB":
        rgb = im.split()
        if ImageChops.difference(rgb[0],rgb[1]).getextrema()[1]!=0: 
            return False
        if ImageChops.difference(rgb[0],rgb[2]).getextrema()[1]!=0: 
            return False
    return True



def speedbinb_unscrambler(Input_img_path, JSON_path, new_image_path):
    """
    Restore the scrambled images from SpeedBinB webreaders.
    Takes a full path to a image file, a full path to accompanying JSON file,
          a full target path to save the unscrambled image file.
    NO Returns
    """
    JSON_read_ok = False
    try:
        with open(JSON_path, "r", encoding="utf-8") as open_JSON_path:
            binb_json = json.load(open_JSON_path)
            JSON_read_ok = True
    except:
        print(f" !Error occured during attempt to load the {os.path.basename(JSON_path)}!'")
    
    if JSON_read_ok == True:
        ## Does .convert("RGB") or .convert("L") would be better for below?
        scrambled_img = Image.open(Input_img_path)
        if is_greyscale(scrambled_img):
            img_mode = "L"
            scrambled_img.convert("L")
            blank_color = (255)
        else:
            img_mode = "RGB"
            blank_color = (255,255,255)
        new_img_resolution = ( int(binb_json["views"][0]["width"]), int(binb_json["views"][0]["height"]) )
        ## SWITCH AS NECESSARY, Pillow grayscale conversion  engine does result in very very minor color shift
        ## However reduces the filesize by 50% on average
        #new_img = Image.new(mode="RGB", size=new_img_resolution, color=(255,255,255))
        new_img = Image.new(mode=img_mode, size=new_img_resolution, color=blank_color)
        
        for slice in binb_json["views"][0]["coords"]:
            ## '+' is a special character for regex
            coords_list = re.split(r",|\+|>", slice)
            ## Cleaning the formatting on JSON
            coords_list[0] = coords_list[0].strip('i:')
            ## Using list comprehension to convert all elements to int
            coords_list = [int(elem) for elem in coords_list]
            ## coords_list: [0 Starting_X_coord] [1 Starting_Y_coord] [2 Size_X] [3 Size_Y] [4 Target_X_coord] [5 Target_Y_coord]
            ## From Photoshop, each value can actually be offset by: However, no indication that the SpeedBinB JS actually does this
            ## "starting_x_coord_-4 ,starting_y_coord_-4 +size_x_+8 ,size_y_+8 >final_x_coord-4 ,final_y_coord-4"
            pillow_right_coord = coords_list[0] + coords_list[2]
            pillow_lower_coord = coords_list[1] + coords_list[3]
            crop_coordinates = ( coords_list[0], coords_list[1], pillow_right_coord, pillow_lower_coord)
            cropped_portion = scrambled_img.crop(box=crop_coordinates)
            target_coordinates = ( coords_list[4], coords_list[5] )
            new_img.paste(cropped_portion, box=target_coordinates)
        
        #new_img.show(title="Unscrambled Image")
        new_img.save(new_image_path, format="png", optimize=True, compress_level=9)



def main():
    print("\n    ====================================")
    print("    ||     7-iro Comics.jp Ripper     ||")
    print("    ====================================\n")
    print("Various folders will be created in the script's directory for archival purpose.")
    print("Completed .png images can be found in 'unscrambled' subfolders.")
    Input_URL = input("Please enter the free WebReader URL (e.g. 'https://7irocomics.jp/webcomic/content001/25/'):\n> ")
    if ("7irocomics.jp" not in Input_URL.lower()) and ("webcomic" not in Input_URL.lower()):
        print(">!ERROR!< ~Invalid URL provided! Must contain '7irocomics.jp' and 'webcomic'.")
        raise SystemExit
    if not Input_URL.endswith('/'):
        Input_URL += '/'
    
    
    #### Initialize Requests for downloads ####
    User_Agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
    Rheaders = {"User-Agent":User_Agent}
    Rsession = requests.session()
    Rsession.headers.update(Rheaders)
    
    #### Parsing the Webreader HTML for title & links to all JSON raw data ####
    Reader_HTML = Rsession.get(Input_URL, allow_redirects=True).text
    ## Using xml.etree.ElementTree might be better but rescinded due to vulnerabilities issue 
    Reader_HTML_split = Reader_HTML.splitlines()
    Raw_PTIMG_list, title = [], None
    for line in Reader_HTML_split:
        if "<title>" in line:
            # title = line.split("<title>", 1)[1].split("</title>", 1)[0].strip()
            ## Index-based alternative
            title = line[line.find("<title>")+len("<title>"):line.rfind("</title>")].strip()
        if "data-ptimg=" in line:
            sections = line.split()
            for section in sections:
                if "data-ptimg=" in section:
                    section = section.replace('data-ptimg=', '')
                    Raw_PTIMG_list.append(section.strip('"'))
    Total_count = len(Raw_PTIMG_list)
    print(f" ~Found {Total_count} images to download")
    
    
    #### Housekeeping; folder creations, etc. ####
    script_folder_path = os.path.dirname(os.path.abspath(__file__))
    ## TODO: Find a way to get the chapter number
    path_list = Input_URL.split('/')
    ## Sanitizing list for Win32 folder naming using list comprehension
    path_list = [re.sub(r'[\\/*?:"<>|]+', '', elem) for elem in path_list]
    ## Removing empty elems from list w/ list comprehension
    path_list = [elem for elem in path_list if elem.strip()]
    
    if title:
        download_folder_path = script_folder_path + os.sep + "raws_downloaded" + os.sep + title + os.sep + path_list[-1]
        unscrambled_folder_path = script_folder_path + os.sep + "unscrambled" + os.sep + title + os.sep + path_list[-1]
    else:
        download_folder_path = script_folder_path + os.sep + "raws_downloaded" + os.sep + path_list[-2] + os.sep + path_list[-1]
        unscrambled_folder_path = script_folder_path + os.sep + "unscrambled" + os.sep + path_list[-2] + os.sep + path_list[-1]
        
    if not os.path.exists(download_folder_path):
        os.makedirs(download_folder_path)
    if not os.path.exists(unscrambled_folder_path):
        os.makedirs(unscrambled_folder_path)
    
    
    #### Looping all the parsed links to download both JSON and images ####
    Current_count = 1
    for Relative_JSON_url in Raw_PTIMG_list:
        Full_JSON_url = Input_URL + Relative_JSON_url
        JSON_filename = Full_JSON_url.rsplit('/', 1)[-1]
        JSON_path = os.path.join(download_folder_path, JSON_filename)
        
        Full_image_url = Input_URL + Relative_JSON_url.replace('.ptimg.json', '.jpg')
        Image_filename = Full_image_url.rsplit('/', 1)[-1]
        Image_path = os.path.join(download_folder_path, Image_filename)
        
        JSON_data = Rsession.get(Full_JSON_url, allow_redirects=True)
        #Is 'wb' write binary necessary?
        with open(JSON_path, 'wb') as write_JSON:
            write_JSON.write(JSON_data.content)
        
        Image_data = Rsession.get(Full_image_url, allow_redirects=True)
        with open(Image_path, 'wb') as write_image:
            write_image.write(Image_data.content)
        
        print(f" {Current_count} / {Total_count}")
        Current_count += 1
    
    
    ####    UNSCRAMBLING PROCESS    ####
    #### Parsing the download folder for .jpg files ####
    print(">Unscrambling downloaded images...")
    JPG_path_list = []
    for root, dirs, files in os.walk(download_folder_path):
        for file in files:
            if file.lower().endswith(".jpg") or file.lower().endswith(".jpeg"):
                file_path = os.path.abspath(os.path.join(root, file))
                JPG_path_list.append(file_path)
    
    #### Looping image unscrambling, assuming that PTIMG.json has roughly the same name as the image file ####
    for Each_JPG_path in JPG_path_list:
        JSON_path = Each_JPG_path.rsplit('.', 1)[0] + ".ptimg.json"
        unscrambled_img_filename = os.path.basename(Each_JPG_path).rsplit('.', 1)[0] + ".png"
        unscrambled_image_path = os.path.join(unscrambled_folder_path, unscrambled_img_filename) 
        speedbinb_unscrambler(Each_JPG_path, JSON_path, unscrambled_image_path)
    print(" ~Unscrambling process finished, check the 'unscrambled' subfolders for the results.")


if __name__ == '__main__':
    main()
    input('Press ANY KEY to exit')