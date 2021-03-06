# -*- coding: utf-8 -*-
"""
Created on Fri May 15 16:48:01 2015

@author: hugo
"""

# from beampy.global_variables import _document, _width, _height,
# _global_counter
from beampy.commands import document
from beampy.functions import render_texts
import json
try:
    from cStringIO import StringIO
except:
    from io import StringIO

import sys
import os
import time
import io

# Get the beampy folder
curdir = os.path.dirname(__file__) + '/'


def save_layout():
    for islide in xrange(document._global_counter['slide']+1):
        slide = document._slides["slide_%i" % islide]
        slide.build_layout()


def reset_module_rendered_flag():
    for slide in document._slides:
        # document._slides[slide].svgout = []
        # document._slides[slide].svglayers = {}
        # document._slides[slide].htmlout = {}
        document._slides[slide].reset_rendered()

        for ct in document._slides[slide].contents:
            document._slides[slide].contents[ct].reset_outputs()
            # document._slides[slide].contents[ct].rendered = False
            # document._slides[slide].contents[ct].exported = False
            # document._slides[slide].contents[ct].svgout = None
            # document._slides[slide].contents[ct].htmlout = None



def save(output_file=None, format=None):
    """
        Function to render the document to html

    """

    if document._quiet:
        sys.stdout = open(os.devnull, 'w')

    texp = time.time()
    bname = os.path.basename(output_file)
    bdir = output_file.replace(bname,'')

    if document._rendered:
        document._rendered = False
        reset_module_rendered_flag()

    file_ext = os.path.splitext(output_file)[-1]

    if 'html' in file_ext or format == 'html5':
        document._output_format = 'html5'
        save_layout()
        # Render glyphs
        render_texts()
        output = html5_export()

    elif 'svg' in file_ext or format == "svg":
        document._output_format = 'svg'
        save_layout()
        # Render glyphs
        render_texts()
        output = svg_export(bdir+'/tmp')
        output_file = None

    elif 'pdf' in file_ext or format == 'pdf':
        document._output_format = 'pdf'
        save_layout()
        # Render glyphs
        render_texts()
        output = pdf_export(output_file)

        output_file = None

    if output_file is not None:
        with open(output_file, 'w') as f:
            f.write(output.encode('utf8'))

    # write cache file
    if document._cache is not None:
        document._cache.write_cache()

    # Set rendered flag to true for the whole document
    document._rendered = True

    print("="*20 + " BEAMPY END (%0.3f seconds) "%(time.time()-texp)+"="*20)


def pdf_export(name_out):

    # External tools cmd
    inkscapecmd = document._external_cmd['inkscape']
    pdfjoincmd = document._external_cmd['pdfjoin']

    # use inkscape to translate svg to pdf
    svgcmd = inkscapecmd+" --without-gui  --file='%s' --export-pdf='%s' -d=300"
    bdir = os.path.dirname(name_out)

    print('Render svg slides')
    aa = svg_export(bdir+'/tmp')

    print('Convert svg to pdf with inkscape')
    output_svg_names = []
    for islide in xrange(document._global_counter['slide']+1):
        print('slide %i'%islide)
        for layer in range(max(document._slides['slide_%i'%islide].svglayers) + 1):
            print('layer %i'%layer)
            #Use inkscape to render svg to pdf
            res = os.popen(svgcmd%(bdir+'/tmp/slide_%i-%i.svg'%(islide, layer),
                                   bdir+'/tmp/slide_%i-%i.pdf'%(islide, layer))
                          )
            res.close()

            output_svg_names += ['slide_%i-%i'%(islide, layer)]

    #join all pdf
    res = os.popen(pdfjoincmd+' %s -o %s'%(' '.join(['"'+bdir+'/tmp/%s.pdf"'%sname for sname in output_svg_names]), name_out))
    output = res.read()

    res.close()
    msg = "Saved to %s"%name_out
    #os.system('rm -rf %s'%(bdir+'/tmp/slide_*'))

    return msg


def svg_export(dir_name, quiet=False):
    # Export evry slides in svg inside a given folder

    if quiet:
        sys.stdout = open(os.devnull, 'w')

    try:
        os.mkdir(dir_name)
    except:
        pass

    if dir_name[-1] != '/':
        dir_name += '/'

    for islide in xrange(document._global_counter['slide']+1):
        print("Export slide %i"%islide)

        slide = document._slides["slide_%i"%islide]

        # Render the slide
        slide.newrender()

        # The global svg glyphs need also to be added to the html5 page
        if 'glyphs' in document._global_store:
            glyphs_svg = '<defs>%s</defs>' % (
                ''.join([glyph['svg'] for glyph in document._global_store['glyphs'].itervalues()]).decode('utf-8',
                                                                                                          errors='replace'))
        else:
            glyphs_svg = ''

        # join all svg defs
        def_svg = '<defs>%s</defs>'%(''.join(slide.svgdefout).decode('utf-8', errors='replace'))
        for layer in range(max(slide.svglayers) + 1):

            # save the list of rendered svg to a new dict as a string
            tmp = slide.svgheader + glyphs_svg + def_svg

            # Join all the svg contents
            tmp += slide.svglayers[layer].decode('utf-8', errors='replace')

            # Add the svgfooter
            tmp += slide.svgfooter

            with io.open(dir_name+'slide_%i-%i.svg'%(islide, layer), 'w', encoding='utf8') as f:
                f.write(tmp)

    return "saved to "+dir_name


def html5_export():

    with open(curdir+'statics/jquery.js','r') as f:
        jquery = f.read()

    with open(curdir+'statics/header_V2.html','r') as f:
        output = f.read()%jquery

    # Add the style
    htmltheme = document._theme['document']['html']
    output += """
    <!-- Default Style -->
    <style>
      * { margin: 0; padding: 0;
        -moz-box-sizing: border-box; -webkit-box-sizing: border-box;
        box-sizing: border-box; outline: none; border: none;
        }

      body {
        width: """+str(document._width)+"""px;
        height: """+str(document._height)+"""px;
        margin-left: -"""+str(int(document._width/2))+"""px; margin-top: -"""+str(int(document._height/2))+"""px;
        position: absolute; top: 50%; left: 50%;
        overflow: hidden;
        display: none;
        background-color: #ffffff;

      }

      section {
        position: absolute;
        width: 100%; height: 100%;
      }


      html { background-color: """+str(htmltheme['background_color'])+""";
        height: 100%;
        width: 100%;
      }

      video {
        visibility: hidden;
      }


      body.loaded { display: block;}
    </style>

    """
    # Loop over slides in the document
    # If we directly want to charge the content in pure html
    tmpout = {}
    tmpscript = {}
    global_store = ''
    for islide in xrange(document._global_counter['slide']+1):

        tnow = time.time()

        slide_id = "slide_%i"%islide
        tmpout[slide_id] = {}
        slide = document._slides[slide_id]

        # Render the slide
        slide.newrender()

        # Add a small peace of svg that will be used to get the data from the global store
        tmpout[slide_id]['svg'] = [] # Init the store for the differents layers
        #tmpout[slide_id]['layers_nums'] = max(slide.svglayers)
        tmpout[slide_id]['layers_nums'] = slide.num_layers
        tmpout[slide_id]['svg_header'] = slide.svgheader
        tmpout[slide_id]['svg_footer'] = slide.svgfooter

        # save the list of rendered svg to a new dict as a string that is loaded globally in the html
        #tmp = ''.join(slide.svgout).decode('utf-8', errors='replace')
        modulessvgdefs = ''.join(slide.svgdefout).decode('utf-8', errors='replace')
        global_store += "<svg><defs>" + modulessvgdefs

        for layer in range(slide.num_layers+1):
            print('write layer %i'%layer)
            # Export svg defs to the global store
            if layer in slide.svglayers:
                layer_content = slide.svglayers[layer].decode('utf-8', errors='replace')
            else:
                layer_content = '' #create an empty content (usefull when only html are present in one slide)

            global_store += "<g id='slide_{i}-{layer}'>{content}</g>".format(i=islide, layer=layer, content=layer_content)
            # Create an svg use for the given layer
            tmpout[slide_id]['svg'] += ['<use xlink:href="#slide_{i}-{layer}"/>'.format(i=islide, layer=layer)]

        global_store += '</defs></svg>'
        
        if slide.animout is not None:
            tmpout[slide_id]['svganimates'] = {}
            headers = []
            for ianim, data in enumerate(slide.animout):
                headers += [data['header']]
                data.pop('header')
                tmpout[slide_id]['svganimates'][data['anim_num']] = data

            # Add cached images to global_store
            # old comparision headers != []
            if headers:
                tmp = ''.join(headers).decode('utf-8', errors='replace')
                global_store += "<svg>%s</svg>"%(tmp)

        if slide.scriptout is not None:
            tmpscript['slide_%i'%islide] = ''.join(slide.scriptout)
            
        if slide.htmlout is not None:
            for layer in slide.htmlout:
                global_store += '<div id="html_store_slide_%i-%i">%s</div>'%(islide, layer,
                                                                             ''.join(slide.htmlout[layer]))

        print("Done in %0.3f seconds"%(time.time()-tnow))

        
    # Create a json file of all slides output (refs to store)
    jsonfile = StringIO()
    json.dump(tmpout,jsonfile, indent=None)
    jsonfile.seek(0)

    # The global svg glyphs need also to be added to the html5 page
    if 'glyphs' in document._global_store:
        glyphs_svg='<svg id="glyph_store"><defs>%s</defs></svg>'%( ''.join( [ glyph['svg'] for glyph in document._global_store['glyphs'].itervalues() ] ) )
        output += glyphs_svg

    # Add the svg content
    output += u"".join( global_store )    
    
    
    # Create store divs for each slides
    output += '<script> slides = eval( ( %s ) );</script>'%jsonfile.read()


    # Javascript output
    # format: scripts_slide[slide_i]['function_name'] = function() { ... }
    if tmpscript != {}:
        bokeh_required = False
        output += '\n <script> scripts_slide = {}; //dict with scrip function for slides \n'
        for slide in tmpscript:
            output += '\nscripts_slide["%s"] = {};\n scripts_slide["%s"]%s; \n'%(slide, slide, tmpscript[slide])
            if 'bokeh' in tmpscript[slide].lower():
                bokeh_required = True

        output += '</script>\n'

        if bokeh_required:
            # TODO: Cache downloaded files !
            from bokeh.resources import CDN
            import urllib2

            css_out = u'<style>'
            for cssurl in CDN.css_files:
                print('Download %s'%cssurl)
                response = urllib2.urlopen(cssurl)
                csst = response.read()
                css_out += csst.decode('utf-8', errors='replace')
            css_out += u'</style>'

            js_out = u'<script>'
            for jsurl in CDN.js_files:
                print('Download %s'%jsurl)
                response = urllib2.urlopen(jsurl)
                jst = response.read()
            js_out += u'</script>'
            js_out += jst.decode('utf-8', errors='replace')


            output += css_out + js_out

    with open(curdir+'statics/footer_V2.html','r') as f:
        output += f.read()

    return output


def check_content_type_change(slide, nothtml=True):
    """
        Function to change type of some slide contents (like for video html -> svg ) when render is changer from html5 to another
    """

    for ct in slide['contents']:
        if nothtml:
            if 'type_nohtml' in ct:
                print('done')
                ct['original_type'] = copy(ct['type'])
                ct['type'] = ct['type_nohtml']
        else:
            if 'original_type' in ct:
                ct['type'] = ct['original_type']


def display_matplotlib(slide_id, show=False):
    """
        Display the given slide in a matplotlib figure
    """
    from matplotlib import pyplot
    from PIL import Image
    from numpy import asarray

    if document._quiet:
        sys.stdout = open(os.devnull, 'w')

    # Set document format to svg
    oldformat = document._output_format
    document._output_format = 'svg'

    # Render all text in slides
    render_texts()
    slide = document._slides[slide_id]

    # Render the slide
    slide.newrender()

    svgout = slide.svgheader

    # Export glyphs
    if 'glyphs' in document._global_store:
        glyphs_svg = '<defs>%s</defs>' % (''.join([glyph['svg'] for glyph in document._global_store['glyphs'].itervalues()]))
        svgout += glyphs_svg.decode('utf-8', errors='replace')

    # join all svg defs
    svgout += '<defs>%s</defs>' % (''.join(slide.svgdefout).decode('utf-8', errors='replace'))

    for layer in range(max(slide.svglayers) + 1):

        # Join all the svg contents
        svgout += slide.svglayers[layer].decode('utf-8', errors='replace')

    # Add the svgfooter
    svgout += slide.svgfooter

    # Write it to a file
    tmpname = './.%s' % slide_id
    with io.open(tmpname+'.svg', 'w', encoding='utf8') as f:
        f.write(svgout)

    # Reset document format to oldformat
    reset_module_rendered_flag()
    document._output_format = oldformat

    # Change it a png
    inkscapecmd = document._external_cmd['inkscape']
    # use inkscape to translate svg to pdf
    svgcmd = inkscapecmd+" --without-gui  --file='%s' --export-png='%s' -b='white' -d=300"
    os.popen(svgcmd % (tmpname+'.svg', tmpname+'.png'))

    img = asarray(Image.open(tmpname+'.png'))

    # Remove files
    os.unlink(tmpname+'.svg')
    os.unlink(tmpname+'.png')

    pyplot.figure(dpi=300)
    pyplot.imshow(img)
    # pyplot.axis('off')
    pyplot.xticks([])
    pyplot.yticks([])
    pyplot.tight_layout()

    
    if show:
        pyplot.show()
