from jinja2 import Environment, FileSystemLoader, environmentfilter
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, send_from_directory, safe_join
from docutils.core import publish_parts
import os.path
import os
import fileinput
import codecs


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'pages')
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

BLOG_DIR = os.path.join(os.path.dirname(__file__), 'blog')
MEETINGS_DIR = os.path.join(os.path.dirname(__file__), 'meetings')

app = application = Flask(__name__, template_folder=TEMPLATE_DIR, static_url_path='/_static', static_folder=STATIC_DIR)
app.debug =  bool(os.environ.get('APP_DEBUG', 'False'))

@app.after_request
def call_after_request_callbacks(response):
    for callback in getattr(g, 'after_request_callbacks', ()):
        response = callback(response)
    return response

def after_this_request(f):
    if not hasattr(g, 'after_request_callbacks'):
        g.after_request_callbacks = []
    g.after_request_callbacks.append(f)
    return f


@app.template_filter('restructuredtext')
def restructuredtext(value):
    parts = publish_parts(source=value, writer_name="html")
    return parts['html_body']


@app.url_value_preprocessor
def pull_lang(endpoint, values):
    if not values:
        return
    g.lang=values.pop('lang', None)

@app.url_defaults
def set_lang(endpoint, values):
    if not values:
        return
    if 'lang' in values:
        return
    if hasattr(g, 'lang'):
        values['lang'] = g.lang

@app.before_request
def detect_theme():
    theme = 'light'
    if 'style' in request.cookies:
        theme = request.cookies['style']
    if 'theme' in request.args.keys():
        theme = request.args['theme']
    if not os.path.isfile(safe_join('static/styles', '%s.css' % theme)):
        theme = 'light'
    g.theme = theme
    @after_this_request
    def remember_theme(resp):
        if g.theme == 'light' and 'style' in request.cookies:
            resp.delete_cookie('style')
        elif g.theme != 'light':
            resp.set_cookie('style', g.theme)
        return resp


@app.errorhandler(404)
def page_not_found(error):
    return render_template('global/error_404.html'), 404
    
@app.route('/')
def main_index():
    return redirect(url_for('site_show', lang='en'))



@app.route('/<string:lang>/site/')
@app.route('/<string:lang>/site/<path:page>')
def site_show(page='index'):
    if page.endswith('.html'):
        return redirect(url_for('site_show', page=page[:-5]))
    name = 'site/%s.html' % page
    page_file = safe_join(TEMPLATE_DIR, name)
    
    # bah! those damn users all the time!
    if not os.path.exists(page_file):
        abort(404)
    
    # hah!
    return render_template(name, page=page)

@app.route('/<string:lang>/meetings/')
def meetings_index():
    return render_template('meetings/index.html')

@app.route('/<string:lang>/meetings/<int:id>')
def meetings_show(id, log=False, rst=False):
    """
    Render the meeting X.
    Either display the raw IRC .log or render as html and include .rst as header if it exists
    """
    # generate file name for the raw meeting file(and header)
    lname = str(id) + '.log'
    hname = str(id) + '.rst'
    lfile = safe_join(MEETINGS_DIR, lname)
    hfile = safe_join(MEETINGS_DIR, hname)
    
    # check if meeting file exists and throw error if it does not..
    if not os.path.exists(lfile):
        abort(404)
    
    # if the user just wanted the .log
    if log:
        # hmm... maybe replace with something non-render_template like?
        #        return render_template('meetings/show_raw.html', log=log)
        return send_from_directory(MEETINGS_DIR, lname, mimetype='text/plain')
    
    log=''
    header=None
    
    # try to load header if that makes sense
    if os.path.exists(hfile):
        # if the user just wanted the .rst...
        if rst:
            return send_from_directory(MEETINGS_DIR, hname, mimetype='text/plain')
        
        # open the file as utf-8 file
        with codecs.open(hfile, encoding='utf-8') as fd:
            header = fd.read()
    elif rst:
        abort(404)
    
    # load log
    with codecs.open(lfile, encoding='utf-8') as fd:
        log = fd.read()
    
    return render_template('meetings/show.html', log=log, header=header, id=id)
     

@app.route('/<string:lang>/meetings/<int:id>.log')
def meetings_show_log(id):
    return meetings_show(id, log=True)

@app.route('/<string:lang>/meetings/<int:id>.rst')
def meetings_show_rst(id):
    return meetings_show(id, rst=True)

@app.route('/<string:lang>/download')
def downloads_list():
    # TODO: read mirror list or list of available files
    return render_template('downloads/list.html')

@app.route('/<string:lang>/download/<path:file>')
def downloads_select(file):
    # TODO: implement
    pass

@app.route('/download/<string:protocol>/any/<path:file>')
@app.route('/download/<string:protocol>/<string:mirror>/<path:file>')
def downloads_redirect(protocol, file, mirror=None):
    # TODO: implement
    pass



def render_blog_entry(slug):
    """
    Render the blog entry
    TODO:
    - caching
    - move to own file
    """
    # check if that file actually exists
    path = safe_join(BLOG_DIR, slug + ".rst")
    if not os.path.exists(path):
        abort(404)

    # read file
    with codecs.open(path, encoding='utf-8') as fd:
        content = fd.read()
    
    return publish_parts(source=content, source_path=BLOG_DIR, writer_name="html")



@app.route('/<string:lang>/blog/')
@app.route('/<string:lang>/blog/page/<int:page>')
def blog_index(page=0):
    # TODO: implement
    pass

@app.route('/<string:lang>/blog/entry/<path:slug>')
def blog_entry(slug):
    # try to render that blog entry.. throws 404 if it does not exist
    parts = render_blog_entry(slug)
    
    if parts:
        # now just pass to simple template file and we are done
        return render_template('blog/entry.html', parts=parts, title=parts['title'], body=parts['fragment'])
    else:
        abort(404)
    

@app.route('/feed/blog/rss')
def blog_rss():
    # TODO: implement
    pass

@app.route('/feed/blog/atom')
def blog_atom():
    # TODO: implement
    pass




## legacy stuff:

@app.route('/meeting<int:id>')
@app.route('/meeting<int:id>.html')
def legacy_meeting(id):
    return redirect(url_for('meetings_show', id=id, lang='en'))

@app.route('/status-<int:year>-<int:month>-<int:day>')
@app.route('/status-<int:year>-<int:month>-<int:day>.html')
def legacy_status(year, month, day):
    return redirect(url_for('blog_entry', lang='en', slug=('%s/%s/%s/status' % (year, month, day))))

LEGACY_MAP={
    'download': 'downloads_list'
}

@app.route('/<string:f>_<string:lang>')
@app.route('/<string:f>_<string:lang>.html')
@app.route('/<string:f>')
@app.route('/<string:f>.html')
def legacy_show(f):
    lang = 'en'
    if hasattr(g, 'lang') and g.lang:
        lang = g.lang
    if f in LEGACY_MAP:
        return redirect(url_for(LEGACY_MAP[f], lang=lang))
    else:
        return redirect(url_for('site_show', lang=lang, page=f))



if __name__ == '__main__':
    app.run(debug=True)
