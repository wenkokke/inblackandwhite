from __future__ import print_function
from os         import system, remove
from os.path    import basename, dirname, splitext
from urllib     import urlretrieve
from itertools  import islice
from time       import sleep
from urlparse   import urlparse
from wand.image import Image
from pytumblr   import TumblrRestClient
from yaml       import load

def getlastid(path):
    """Read the first id from an id file."""
    with open(path, 'r') as fp:
        return long(fp.readline())

def setlastid(path,id,n=10):
    """Prepend an id to an id file, keep a log of at least n previous ids."""
    with open(path, 'r') as fp:
        lastn = list(islice(fp,n))
    with open(path, 'w') as fp:
        fp.write("{}\n".format(id))
        for id in lastn:
            fp.write("{}\n".format(id.strip()))

def getphotos(client,blogname,lastid,offset=0,limit=20):
    """Read photo-posts from a Tumblr blog until an id matches lastid."""
    result = []
    photos = client.posts(blogname, type='photo', limit=limit, offset=offset)['posts']
    for photo in photos:
        if photo['id'] == lastid:
            return result
        else:
            result.append(photo)
    sleep(1) # to avoid scaring tumblr
    result.extend(getphotos(client,blogname,lastid,offset=offset+limit,limit=limit))
    return result

def handlephotos(client,blogname,lastid_file,posts):
    """Download posts, convert them to grayscale, and upload them to blogname."""
    for post in posts:
        print("handle: ", post['post_url'])
        index = 0
        image_files = []
        for photo in post['photos']:
            image_file = downloadphoto(post, photo, index)
            convertphoto(image_file)
            image_files.append(image_file)
            index += 1
        uploadphoto(client,blogname,post,image_files)
        setlastid(lastid_file,post['id'])
        for image_file in image_files: remove(image_file)

def downloadphoto(post,photo,index):
    """Download a photo-post to a file, return the filename."""
    src = photo['original_size']['url']
    ext = splitext(urlparse(src).path)[1]
    dst = "post-{}-{}{}".format(post['id'],index,ext)
    urlretrieve(src,dst)
    return dst

def convertphoto(image_file):
    """Read image from file, convert it to grayscale and overwrite the file with the new image."""
    with Image(filename=image_file) as image:
      image.type = 'grayscale'
      image.save(filename=image_file)

def uploadphoto(client,blogname,post,image_files):
    """Upload a photo-post to Tumblr, replacing the photo with image_files and adding B&W related tags."""
    tags = ['black and white', 'bnw', 'monochrome']
    tags.extend(post['tags'])
    client.create_photo(blogname, state = 'queue', tags = tags, link = post['post_url'], data = image_files)

# load the configuration file
with open("config.yaml",'r') as fp: config = load(fp)
    
# setup a tumblr client
client = TumblrRestClient(
    consumer_key    = config['consumer_key'],
    consumer_secret = config['consumer_secret'],
    oauth_token     = config['oauth_token'],
    oauth_secret    = config['oauth_secret'])
    
# retrieve last-handled id from lastid-file
lastid = getlastid(config['lastid_file'])
    
# retrieve new photo-posts from tumblr
posts = getphotos(client,config['source_blog'],lastid)

# attempt to handle posts (if any)
if len(posts) == 0:
    print("no new posts")
else:
    handlephotos(client,config['target_blog'],config['lastid_file'],reversed(posts))

system("pause")