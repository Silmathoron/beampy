# -*- coding: utf-8 -*-
"""
Created on Sun Oct 25 20:33:18 2015

@author: hugo
"""
from beampy import document
from beampy.functions import (gcs, create_element_id, check_function_args,
                              get_command_line, convert_unit,
                              pre_cache_svg_image, print_function_args)

from beampy.geometry import positionner, distribute
import sys
import time
import inspect


class slide():
    """
    Add a slide to the presentation.

    Parameters
    ----------

    title : str or None, optional
        Set the title of the slide (the default value is None)

    background : str, optional
        Background color of the slide (the default value is "white"). Accept svg color name or HTML hex value.

    layout: function or None, optional
        Function containing beampy modules that will be displayed as slide background.

        >>> slide(layout=my_function)

    """

    def __init__(self, title=None, **kwargs):

        # Add a slide to the global counter
        if 'slide' in document._global_counter:
            document._global_counter['slide'] += 1
        else:
            document._global_counter['slide'] = 0
        # Init group counter
        document._global_counter['group'] = 0

        # check args from THEME
        self.args = check_function_args(slide, kwargs)

        # The id for this slide
        self.id = gcs()
        self.slide_num = document._global_counter['slide']

        # Change from dict to class
        self.tmpout = ''
        self.contents = {}
        self.element_keys = []
        self.cpt_anim = 0
        self.num = document._global_counter['slide']+1
        self.title = title
        self.curwidth = document._width
        self.num_layers = 0 # Store the number of layers in this slide

        # Store all outputs
        self.svgout = []
        self.svgdefout = []  # Store module definition for slide
        self.htmlout = {}  # Html is a dict, each key dict is a layer htmlout[0] = [html, html, html] etc...
        self.scriptout = []
        self.animout = []
        self.svgheader = ''
        self.svgfooter = '\n</svg>\n'
        self.svglayers = {}  # Store slide final svg (without svg defs stored in self.svgdefout) for the given layer

        # Do we need to render the THEME layout on this slide
        self.render_layout = True

        # Add the slide to the document contents list
        document._slides[self.id] = self

        # Manage groups inside one slide the lower level of group is 0 and correspond
        # to the main slide
        self.groupsid = {}
        self.cur_group_level = -1
        g0 = group(x=0, y=0, width=document._width, height=document._height)
        self.groupsid[0] = [g0.id]  # store groups id objects in this list

        if title is not None:
            from beampy.modules.title import title as bptitle
            self.title_element = bptitle(title)
            self.ytop = float(convert_unit(self.title.reserved_y))
        else:
            self.ytop = 0
            self.title_element = None

        # Add ytop to the slide main group
        g0.yoffset = self.ytop

    def add_module(self, module_id, module_content):
        t = time.time()
        # Add a module to the current slide
        self.element_keys += [module_id]
        self.contents[module_id] = module_content

        # Check if it's a new group or not
        if module_content.type != 'group':
            self.contents[self.groupsid[self.cur_group_level][-1]].add_elements_to_group(module_id, module_content)
            # Add the id of the group to the module
            self.contents[module_id].group_id = self.groupsid[self.cur_group_level][-1]
            # Todo[improvement]: register the group tree for a given module not just the last group
        else:

            if self.cur_group_level > 0:
                # Add this group id to the previous group
                if module_content.parentid is not None:
                    # print("add parent %s"%module_content.parentid)
                    self.contents[module_content.parentid].add_elements_to_group(module_id, module_content)

                if self.cur_group_level not in self.groupsid:
                    self.groupsid[self.cur_group_level] = [ module_id ]
                else:
                    self.groupsid[self.cur_group_level] += [ module_id ]

        # print('Element %s added to slide in %f'%(str(module_content.name), time.time()-t))

    def remove_module(self, module_id):
        # Remove a module
        self.element_keys.pop(self.element_keys.index(module_id))
        # Remove the module from it's group
        gid = self.contents[module_id].group_id
        self.contents[gid].remove_element_in_group(module_id)
        # Remove the module from contents main store
        self.contents.pop(module_id)

    def add_rendered(self, svg=None, svgdefs=None, html=None, js=None, animate_svg=None, layer=0):

        if svg is not None:
            self.svgout += [svg]

        if svgdefs is not None:
            self.svgdefout += [svgdefs]

        if html is not None:
            if layer in self.htmlout:
                self.htmlout[layer] += [html]
            else:
                self.htmlout[layer] = [html]

        if js is not None:
            self.scriptout += [js]

        if animate_svg is not None:
            self.animout += [animate_svg]

    def reset_rendered(self):
        self.svgout = []
        self.svgdefout = []  # Store module definition for slide
        self.htmlout = {}
        self.svglayers = {}
        self.scriptout = []
        self.animout = []

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        # Check layers inside this slide
        self.check_modules_layers()

    def check_modules_layers(self):
        """
        Function to check the consistency of layers in the slide.
        To do so:

        1- Get the number of layers

        2- Resolve string layers to replace 'max' statement with the slide number of layer
           expl: 'range(0-max-1)' or '[0,max]'

        3- Check that layers are consecutive numbers from 0 -> max
        """

        # Get the max layers
        for mid in self.contents:
            module = self.contents[mid]
            if not isinstance(module.layers, str):
                maxmodulelayers = max(module.layers)
                if maxmodulelayers > self.num_layers:
                    self.num_layers = maxmodulelayers

        layers_in_slide = []
        for mid in self.contents:
            module = self.contents[mid]

            # Resolve string args 'max' in layers
            if isinstance(module.layers, str):
                if 'range' in module.layers:
                    lmax = self.num_layers + 1
                else:
                    lmax = self.num_layers

                module.add_layers(eval(module.layers.replace('max', str(lmax))))

            # Check the consecutivity of layers
            for layer in module.layers:
                if layer not in layers_in_slide:
                    layers_in_slide += [layer]

        layers_in_slide = sorted(layers_in_slide)
        if layers_in_slide != range(0, self.num_layers+1):
            raise ValueError('Layers are not consecutive. I got %s, I should have %s'%(str(layers_in_slide),
                                                                                       str(range(0, self.num_layers+1))))

        # Propagate layer of modules inside groups
        for mid in self.contents:
            if self.contents[mid].type == 'group':
                self.contents[mid].propagate_layers()

    def show(self):
        from beampy.exports import display_matplotlib
        display_matplotlib(self.id, True)

    def build_layout(self):
        """
            Function to build the layout of the slide,
            elements defined in bacground inside the theme file
        """

        # Check if we have a background layout to render
        if self.render_layout:
            if self.args['layout'] is not None and 'function' in str(type(self.args['layout'])):

                # We need to restor the id of the slide for each module produced in the layout
                save_global_ct = document._global_counter['slide'] # backup the total number of slides
                document._global_counter['slide'] = self.slide_num # put the slide number in the counter

                # Need to store elements keys last index to retrieve elements added by theme layout function
                first_elem_i = len(self.element_keys)

                # Run the layout function (which contains beampy modules)
                self.args['layout']( )

                # Loop over elements to add them to all layers in the slide
                for eid in self.element_keys[first_elem_i:]:
                    self.contents[eid].add_layers(range(self.num_layers+1))

                document._global_counter['slide'] = save_global_ct # restor the slide counter

    def newrender(self):
        """
            Render the slide content.
            - Transform module to svg or html
            - Loop over groups
            - Place modules
            - write the final svg
        """
        print('-' * 20 + ' slide_%i ' % self.num + '-' * 20)

        if self.title_element is not None:
            self.title_element.add_layers(range(self.num_layers+1))

        # First loop over slide's modules to render them (to get height and width)
        # Todo: do that using multiprocessing
        for i, key in enumerate(self.element_keys):
            elem = self.contents[key]

            if elem.type != 'group':
                if not elem.rendered:
                    elem.run_render()

                assert elem.width is not None
                assert elem.height is not None
                # print(elem.width, elem.height)

        # Loop over group level (from the max -> 0)
        print('Number of groups %i' % max(self.groupsid))

        for level in range(max(self.groupsid), -1, -1):

            for curgroupid in self.groupsid[level]:

                curgroup = self.contents[curgroupid]

                #Check group given size
                if curgroup.width is None:
                    auto_width = document._width
                else:
                    auto_width = curgroup.width

                if curgroup.height is None:
                    auto_height = document._height
                else:
                    auto_height = curgroup.height

                # First look at auto positionning for elements in groups
                # Check if their is autox or autoy placement
                if len(curgroup.autoxid) > 0:
                    distribute(curgroup.autoxid, 'hspace', auto_width,
                               offset=curgroup.xoffset, curslide=self)

                if len(curgroup.autoyid) > 0:
                    distribute(curgroup.autoyid, 'vspace', auto_height,
                               offset=curgroup.yoffset, curslide=self)

                # Place the module with these distributed postions
                for elem in curgroup.autoxid + curgroup.autoyid + curgroup.manualid:
                    # Check if the element have already be placed (html could be part of serveral groups level)
                    if 'final' not in self.contents[elem].positionner.x:
                        self.contents[elem].positionner.place( (auto_width, auto_height),
                                                                curgroup.yoffset )

                # Compute the real group size if no size (width or height) are given in group args
                if curgroup.width is None :
                    allxw = [ (self.contents[eid].positionner.x['final'],
                               self.contents[eid].positionner.width) for eid in curgroup.elementsid ]

                    minx = min([i[0] for i in allxw])
                    maxx = max([i[0]+i[1] for i in allxw])

                    width = maxx - minx
                    # print('group width %f'%width)
                    curgroup.width = width

                    # Need to reloop over groups elements to increment dx as they have been positionned with slide width
                    for eid in curgroup.elementsid:
                        self.contents[eid].positionner.x['final'] -= minx

                if curgroup.height is None:
                    allyh = [ (self.contents[eid].positionner.y['final'],
                               self.contents[eid].height) for eid in curgroup.elementsid ]

                    miny = min([i[0] for i in allyh])
                    maxy = max([i[0]+i[1] for i in allyh])
                    height = maxy - miny
                    # print('group height %f'%height)
                    curgroup.height = height

                    # Need to reloop over groups elements to increment dy as they have been positionned with slide height
                    for eid in curgroup.elementsid:
                        self.contents[eid].positionner.y['final'] -= miny

                curgroup.update_size( curgroup.width, curgroup.height )
                # print(curgroup.width, curgroup.height)

                # Render the current group (this export final module svg to slide storage)
                curgroup.render()

            if level == 0:
                # The last group (i.e the main frame need to be placed)
                curgroup.positionner.place((document._width, document._height))
                # Export the svg of the slide at a given layer in the slide.svglayers store
                for layer in curgroup.layers:
                    print('export layer %i'%layer)
                    # Check if the layer contain svg outputs (for instance video only layer could exists)
                    try:
                        self.svglayers[layer] = curgroup.export_svg_layer(layer)
                    except Exception as e:
                        # TODO ADD a log to this try
                        print('no svg for layer %i' % layer)
                        

                #Need to deal with html module
                if document._output_format == 'html5':
                    for eid in curgroup.htmlid:
                        # print('Render html %s' % eid)
                        elem = self.contents[eid]
                        # Resolve absolute positionning
                        xgroupsf = sum([self.contents[g].positionner.x['final'] for g in elem.groups_id])
                        ygroupsf = sum([self.contents[g].positionner.y['final'] for g in elem.groups_id])
                        # print(xgroupsf, elem.positionner.x['final'], ygroupsf)
                        elem.positionner.x['final'] += xgroupsf
                        elem.positionner.y['final'] += ygroupsf
                        for layer in elem.layers:
                            htmlo = elem.export_html()
                            self.add_rendered(html=htmlo, layer=layer)

                # Add grid and fancy stuff...
                if document._guide:
                    available_height = document._height - self.ytop
                    out = ''
                    out += '<g><line x1="400" y1="0" x2="400" y2="600" style="stroke: #777"/></g>'
                    out += '<g><line x1="0" y1="%0.1f" x2="800" y2="%0.1f" style="stroke: #777"/></g>' % (
                    self.ytop + available_height / 2.0, self.ytop + available_height / 2.0)
                    out += '<g><line x1="0" y1="%0.1f" x2="800" y2="%0.1f" style="stroke: #777"/></g>' % (
                    self.ytop, self.ytop)
                    self.add_rendered(svg=out)

        # Export the slide svg header
        svg_template = """<?xml version="1.0" encoding="utf-8" standalone="no"?>
        <!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
        "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
        <svg width='{width}px' height='{height}px' style='background-color: {bgcolor};'
        xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="full"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        xmlns:dc="http://purl.org/dc/elements/1.1/"
        xmlns:cc="http://creativecommons.org/ns#"
        xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        shape-rendering="geometricPrecision"
        >"""\

        header_template = svg_template.format(width=document._width,
                                              height=document._height,
                                              bgcolor=self.args['background'])
        self.svgheader = header_template


class beampy_module():
    """
        Base class for creating a module

        Each module need a render method and need to return a register
    """

    rendered = False  # State of the module (True if it has been rendered to an svg
    positionner = None  # Store the positionner (to manage placement in slide)
    content = None  # Store the input content
    type = None  # Define the type of the module
    name = None
    args = {}  # Store the raw dict of passed args (see check_args_from_theme)

    # Storage of render outputs
    svgout = None  # The output of the render
    htmlout = None  # We can store also html peace of code
    jsout = None  # Store javascript if needed
    animout = None  # Store multiple rasters for animation

    call_cmd = ''  # Store the command used in the source script
    call_lines = ''  # Store lines of the call cmd
    id = None  # store a unique id for this module
    group_id = None  # store the group id if the module is inside one group
    start_line = 0
    stop_line = 0

    # Needed args (give some default one)
    x = 0
    y = 0
    width = None
    height = None
    svg_decoration = '' # strore an svg element to add to the elemen group like a rectangle

    #Special args used to create cache id from md5
    args_for_cache_id = None
    #Do cache for this element or not
    cache = True

    #Save the id of the current slide for the module
    slide_id = None

    def __init__(self, **kargs):

        self.check_args_from_theme(kargs)
        self.register()
        print("Base class for a new module")

    def register(self):
        # Function to register the module (run the function add to slide)

        # Save the id of the current slide for the module
        self.slide_id = gcs()

        # Store the list of groups id where the module is finally located (used for html element to
        # resolve final positionning)
        self.groups_id = []

        # Ajout du nom du module
        self.name = self.get_name()

        # Create a unique id for this element
        self.id = create_element_id( self )

        # Store the layers where this module should be printed
        self.layers = [0]
        # Store a boolean to know if this module has been exported to slide store
        self.exported = False

        # Add module to his slide
        document._slides[self.slide_id].add_module(self.id, self)

        self.positionner = positionner( self.x, self.y , self.width, self.height, self.id)

        # Add anchors for relative positionning
        self.top = self.positionner.top
        self.bottom = self.positionner.bottom
        self.left = self.positionner.left
        self.right = self.positionner.right
        self.center = self.positionner.center

        # Report width, height from positionner to self.width, self.height
        self.width = self.positionner.width
        self.height = self.positionner.height

        # Add the source of the script that run this module
        try:
            start, stop, source = get_command_line(self.name)
        except:
            start = 0
            stop = 0
            source = 'None'

        self.call_cmd = source
        self.call_lines = (start, stop)

    def delete(self):
        # Remove from document
        document._slides[gcs()].remove_module(self.id)
        del self

    def reset_outputs(self):
        self.svgout = None  # The output of the render
        self.htmlout = None  # We can store also html peace of code
        self.jsout = None  # Store javascript if needed
        self.animout = None  # Store multiple rasters for animation
        self.rendered = False
        self.exported = False

    def render(self):
        # Define the render for this module (how it is translated to an svg (or html element))
        # If the width/height changes ... update them!
        # self.update_size(new_width, new_height)

        # Store your the render outputs to
        self.svgout = None
        self.htmlout = None
        self.jsout = None
        self.animout = None

    def run_render(self):
        """
            Run the function self.render if the module is not in cache
        """

        # Get the current slide object
        slide = document._slides[gcs()]

        if self.cache and document._cache is not None:
            ct_cache = document._cache.is_cached('slide_%i'%slide.num, self)
            if ct_cache:
                #Update the state of the module to rendered
                self.rendered = True
                try:
                    print("Elem [%s ...] from cache"%self.call_cmd.strip()[:20])
                except:
                    print("Elem %s from cache"%self.name)
            else:
                #print("element %i not cached"%ct['positionner'].id)
                self.render()
                document._cache.add_to_cache('slide_%i'%slide.num, self)
                try:
                    print("Elem [%s ...] rendered"%self.call_cmd.strip()[:20])
                except:
                    print("Elem %s rendered"%self.name)
        else:
            self.render()
            try:
                print("Elem [%s ...] rendered"%self.call_cmd.strip()[:20])
            except:
                print("Elem %s rendered"%self.name)


    def get_name(self):
        # Return the name of the module
        # return str(self.__init__.im_class).split('.')[-1]
        name = str(self.__init__.__self__.__class__).split('.')[-1]

        # For python 3.x compatibility
        if "'>" in name:
            name = name.replace("'>",'')

        return name

    def check_args_from_theme(self, arg_values_dict):
        """
            Function to check input function args.

            Functions args are defined in the default_theme.py
            or if a theme is added the new value is taken rather than the default one
        """

        #Add args value to the module
        self.args = arg_values_dict

        function_name = self.get_name()
        default_dict = document._theme[function_name]
        outdict = {}
        for key, value in arg_values_dict.items():
            #Check if this arguments exist for this function
            if key in default_dict:
                outdict[key] = value
                setattr(self, key, value)
            else:
                print("Error the key %s is not defined for %s module"%(key, function_name))
                print_function_args(function_name)
                sys.exit(1)

        #Check if their is ommited arguments that need to be loaded by default
        for key, value in default_dict.items():
            if key not in outdict:
                setattr(self, key, value)

    def load_extra_args(self, theme_key):
        """
            Function to load default args from the theme for the given theme_key
            and add them to the module
        """
        for key, value in document._theme[theme_key].items():
            if not hasattr(self, key):
                setattr(self, key, value)

                #Add args to the args dictionnary also
                self.args[key] = value

    def load_args(self, kwargs_dict):
        """
            Function to transform input kwargs dict into attribute of the module
        """

        for key, value in kwargs_dict.items():
            setattr(self, key, value)

    def update_size(self, width, height):
        """
            Update the size (width, height) of the current module
        """

        self.positionner.update_size( width, height )
        self.width = self.positionner.width
        self.height = self.positionner.height

    def __repr__(self):
        out = 'module: %s\n'%self.name
        try:
            out += 'source (lines %i->%i):\n%s'%(self.call_lines[0], self.call_lines[1],
                                       self.call_cmd)
        except:
            out += 'source : fail\n'

        out += 'width: %s, height: %s\n'%(str(self.width), str(self.height))

        return out

    # Export methods (how the final svg/html/multisvg is written down)
    # add a group/div object with the good x, y, positions
    def export_svg(self):
        """
            function to export rendered svg in a group positionned in the slide
        """

        out = '<g transform="translate(%s,%s)" class="%s">' % (self.positionner.x['final'],
                                                    self.positionner.y['final'], self.name)

        out += self.svgout

        if document._text_box:
            out +="""<rect x="0"  y="0" width="%s" height="%s"
            style="stroke:#009900;stroke-width: 1;stroke-dasharray: 10 5;
            fill: none;" />""" % (self.positionner.width,
                                  self.positionner.height)

        if self.svg_decoration != '':
            out += self.svg_decoration.format(width=self.positionner.width,
                                              height=self.positionner.height)

        out += '</g>'

        return out

    def export_svg_def(self):
        """
            function to export rendered svg in a group positionned in the slide
        """

        # Todo: add data- to element like data-python="self.call_cmd.strip()"
        out = '<g id="%s" transform="translate(%s,%s)" class="%s" >' % (self.id, self.positionner.x['final'],
                                                    self.positionner.y['final'], self.name)

        out += self.svgout

        if document._text_box:
            out +="""<rect x="0"  y="0" width="%s" height="%s"
            style="stroke:#009900;stroke-width: 1;stroke-dasharray: 10 5;
            fill: none;" />""" % (self.positionner.width,
                                  self.positionner.height)

        if self.svg_decoration != '':
            out += self.svg_decoration.format(width=self.positionner.width,
                                              height=self.positionner.height)

        out += '</g>'

        return out

    def export_html(self):

        out = """<div style="visibility: hidden; position: absolute; left: %spx; top: %spx;"> %s </div></br>"""
        out = out%(self.positionner.x['final'], self.positionner.y['final'], self.htmlout)

        return out

    def export_animation(self):
        # Export animation of list of svg
        if isinstance(self.animout, list):
            # print(self.slide_id, slide.cpt_anim)
            # Pre cache raster images
            frames_svg_cleaned, all_images = pre_cache_svg_image( self.animout )

            # Add an animation to animout dict
            animout = {}
            animout['header'] = "%s"%(''.join(all_images))
            animout['config'] = { 'autoplay':self.autoplay, 'fps': self.fps }
            animout['anim_num'] = self.anim_num
            animout['frames'] = frames_svg_cleaned

            return animout

    def export_animation_layer(self, layer):
        out = '<g id="svganimate_{slide}-{layer}_{id_anim}"' \
              ' transform="translate({x},{y})" onclick="Beampy.animatesvg({id_anim},{fps},{anim_size});"' \
              ' data-slide={slide} data-anim={id_anim} data-fps={fps} data-lenght={anim_size}>{frame_init}</g>'\

        out = out.format(slide=self.slide_id, layer=layer, id_anim=self.anim_num, x=self.positionner.x['final'],
                         y = self.positionner.y['final'], fps=self.fps, anim_size=len(self.animout),
                         frame_init=self.animout[0])
        return out

    def add_border(self, svg_style={'stroke':'red', 'fill':'none', 'stroke-width': 0.5}):
        """
            function to add a border to the given element
        """

        output = '<rect x="0" y="0" width="{width}" height="{height}" '
        for key in svg_style:
            output += '%s="%s" '%(key, svg_style[key])

        output += ' />'

        self.svg_decoration = output

    def add_layers(self, layerslist):
        """
        Function to add this elements to given layers
        :param layerslist: list of layers where the module should be printed
        :return:
        """
        self.layers = layerslist

    def __call__(self, *args, **kwargs):
        # Todo: regegister the module where it is called (use it to recall a module in another slide)
        print("Not implemented")

    def __getitem__(self, item):
        """
        Manage layer of a given module using the python getitem syntax with slicing

        self()[0] -> layer(0)
        self()[:1] -> layer(0,1)
        self()[1:3] -> layer(1,2,3)
        self()[2:] -> layer(2,..,max(layer))
        """

        if isinstance(item, slice):

            if item.step is None:
                step = 1
            else:
                step = item.step

            if item.start is None:
                start = 0
            else:
                start = item.start

            if start < 0:
                start = 'max%i'%start

            if item.stop is None or item.stop > 100000:
                stop = 'max'
            else:
                stop = item.stop

            if stop < 0:
                stop = 'max%i'%stop

            if isinstance(stop, str):
                if isinstance(start, str):
                    self.add_layers('range(%s,max,%i)' % (start, step))
                else:
                    self.add_layers( 'range(%i,max,%i)'%(start, step) )

            else:
                if isinstance(start, str):
                    self.add_layers('range(%s,%i,%i)'%(start, stop+1, step))
                else:
                    self.add_layers(range(start, item.stop+1, step))

        else:
            if isinstance(item, list) or isinstance(item, tuple):
                string_layers = False
                item = list(item)
                for i, it in enumerate(item):
                    if it < 0:
                        item[i] = 'max%i+1'%it
                        string_layers = True

                    if isinstance(it, str):
                        string_layers = True

                if string_layers:
                    # Need to replace ' by None because str([0,'max']) -> "[0,'max']"
                    self.add_layers(str(item).replace("'",""))
                else:
                    self.add_layers(item)

            else:
                if item < 0:
                    item = 'max%i+1'%item

                if isinstance(item, str):
                    self.add_layers('[%s]'%item)
                else:
                    self.add_layers([item])

        return self

    def __len__(self):
        # Need a len of 0 to manager layer [:-1] should return -1
        return 0

    def __enter__(self):
        """
        Implement __enter__ __exit__ to pass the string input of
        the function as comment inside a "with" statement to an input
        of the function via the "process_with" method


        with beampy_module():
            '''
            This text will be stored in the self.input 
            '''

            "this one also"
        """

        # Get the line in the source code of the group
        previous_frame = inspect.currentframe().f_back
        traceback = inspect.getframeinfo(previous_frame)
        self.start_line = traceback.lineno

        return self

    def __exit__(self, exception_type, exception_value, traceback):

        previous_frame = inspect.currentframe().f_back
        traceback = inspect.getframeinfo(previous_frame)
        self.stop_line = traceback.lineno
        self.process_with()

    def process_with(self):
        """
        Function called by the __exit__ function

        Need to be redefined by each module to adjust the behaviours
        of "with :"
        """
        print("With statement not implemented for this module")


class group(beampy_module):
    """Group Beampy modules together and manipulate them as a group

    Parameters
    ----------

    elements_to_group : None or list of beampy.base_module, optional
        List of Beampy module to put inside the group (the default is None).
        This argument allows to group Beampy modules, when `group` is not used
        with the python :py:mod:`with` expression.

    x : int or float or {'center', 'auto'} or str, optional
        Horizontal position for the group (the default is 'center'). See
        positioning system of Beampy.

    y : int or float or {'center', 'auto'} or str, optional
        Vertical position for the group (the default is 'auto'). See
        positioning system of Beampy.

    width : int or float or None, optional
       Width of the group (the default is None, which implies that the width
       is computed to fit the group contents width).

    height : int or float or None, optional
       Height of the group (the default is None). When height is None the
       height is computed to fit the group contents height.

    background : str or None, optional
       Svg color name of the background color for the group (the default is None).

    perentid : str or None, optional
        Beampy id of the parent group (the default is None). This parentid is
        given automatically by Beampy render.


    .. note::

       When the position of a group (`x`, `y`) are relative to a parent group
       and that the parent group has `width`=None or `height`=None and
       positions `x` or `y` equal to 'auto' or 'center', the render will use
       the `slide.curwidth` as `width` and the `document._height` as height.
       This will produce unexpected positioning of child group.


    """

    def __init__(self, elements_to_group=None, x='center', y='auto',
                 width=None, height=None, background=None, parendid=None):

        # Store the input of the module
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.background = background
        self.type = 'group'
        self.content = []
        self.xoffset = 0
        self.yoffset = 0
        self.parentid = parendid # Store the id of the parent group

        #To store elements id to group
        self.elementsid = []
        self.element_keys = []
        self.autoxid = []
        self.autoyid = []
        self.manualid = []
        self.htmlid = [] # Store html module id

        self.content_layer = {} # Store group rendered svg content by layers

        # To store layers inside groups
        # self.layers_elementsid = {}
        # self.svgout_layers = {} # To store svg output by layers

        #Add the parentid if level is more than 1
        slide = document._slides[gcs()]
        if slide.cur_group_level >= 0:
            self.parentid = slide.contents[slide.groupsid[slide.cur_group_level][-1]].id

        #Add group id from the slide groups counter (and add one because it's a new one
        slide.cur_group_level += 1
        self.grouplevel = slide.cur_group_level

        # Add classic register to the slide
        self.register()
        self.group_id = self.id

        if elements_to_group is not None:
            print('TODO: Need to remove these elements from previous group!')
            for e in elements_to_group:
                self.add_elements_to_group(e.id, e)

    def __enter__(self):
        # print('Enter a new group level: %i' % self.grouplevel)
        # Check if we need to update the curwidth of slide
        if self.width is not None:
            document._slides[self.slide_id].curwidth = self.width
        else:
            self.width = document._slides[self.slide_id].curwidth

        return self

    def __exit__(self, type, value, traceback):
        # decrement slide cur_group position
        if self.grouplevel >= 1:
            document._slides[self.slide_id].cur_group_level -= 1

        # Check if we need to update the curwidth of slide to the parent group
        if self.parentid is not None and document._slides[self.slide_id].contents[self.parentid].width is not None:
            document._slides[self.slide_id].curwidth = document._slides[self.slide_id].contents[self.parentid].width

        # print('Leave group return to group level %i'%document._slides[self.slide_id].cur_group_level)

    def add_layers(self, layerslist):
        self.layers = layerslist

    def propagate_layers(self):
        """
        Function to recusivly propagate the layers to group elements
        :return:
        """
        slide = document._slides[self.slide_id]

        for eid in self.elementsid:
            for layer in self.layers:
                if layer not in slide.contents[eid].layers and layer > min(slide.contents[eid].layers):
                    # print('add layer %i to %s' % (layer, slide.contents[eid].name))
                    slide.contents[eid].layers += [layer]

            # Clean layer of elements lower than the minimum of group layer
            for elayer in slide.contents[eid].layers:
                if elayer < min(self.layers):
                    slide.contents[eid].layers.pop(slide.contents[eid].layers.index(elayer))

            # If the elements it's an group with should call the same method to do the recursion
            if slide.contents[eid].type == 'group':
                slide.contents[eid].propagate_layers()

    def add_elements_to_group(self, eid, element):
        #Function to register elements inside the group
        is_auto = False
        self.elementsid += [eid]

        # Add this elementid to the
        #print(element.layers)
        # self.add_element_layers(eid, element.layers)

        if element.x == 'auto':
            self.autoxid += [eid]
            is_auto = True

        if element.y == 'auto':
            self.autoyid += [eid]
            is_auto = True

        if not is_auto:
            self.manualid += [eid]

        if element.type == 'html':
            self.htmlid += [eid]

    def remove_element_in_group(self, elementid):
        """
        Function to remove element from the group key stores

        :param elementid: The id of the module to remove
        """

        for store in [self.autoxid, self.autoyid, self.manualid, self.htmlid, self.elementsid]:
            if elementid in store:
                store.pop( store.index(elementid) )

    def add_svg_content(self, layer, svg):
        # create or append the content_layer store with the given svg

        if layer in self.content_layer:
            self.content_layer[layer] += [svg]
        else:
            self.content_layer[layer] = [svg]

        # Add layer level to group if it's not already created
        if layer not in self.layers:
            self.layers += [layer]

    def render(self):
        """
            group render
        """

        slide = document._slides[self.slide_id]
        self.content = []

        for eid in self.elementsid:

            elem = slide.contents[eid]

            if elem.type == 'group':
                for layer in elem.layers:
                    if layer in elem.content_layer:
                        self.add_svg_content(layer, elem.export_svg_layer(layer))

            else:
                if elem.svgout is not None:
                    if not elem.exported:
                        if elem.type == 'html':
                            if document._output_format != 'html5':
                                slide.add_rendered(svgdefs=elem.export_svg_def())
                                elem.exported = True
                        else:
                            slide.add_rendered(svgdefs=elem.export_svg_def())
                            elem.exported = True

                    for layer in elem.layers:
                        # Check if it's an html element, we need to only output svg for svg format not html
                        if elem.type == 'html':
                            if document._output_format != 'html5':
                                self.add_svg_content(layer, '<use xlink:href="#{id}"></use>'.format(id=elem.id))
                        else:
                            self.add_svg_content(layer, '<use xlink:href="#{id}"></use>'.format(id=elem.id))

            if elem.jsout is not None:
                slide.add_rendered(js=elem.jsout)

            if elem.animout is not None and document._output_format == 'html5':
                if not elem.exported:
                    tmpanim = elem.export_animation()
                    slide.add_rendered(animate_svg=tmpanim)
                    elem.exported = True

                for layer in elem.layers:
                    self.add_svg_content(layer, elem.export_animation_layer(layer))


            # For html objects, they need absolute positionning because they are not included in svg group
            if elem.type == 'html' and elem.htmlout is not None and self.grouplevel > 0:
                # Store the group_id that contains this html
                elem.groups_id += [self.id]
                # remove auto/center args from x and y
                elem.x = '%ipx'%elem.positionner.x['final']
                elem.y = '%ipx'%elem.positionner.y['final']
                # Add the element to the parentgroup
                slide.contents[self.parentid].add_elements_to_group(elem.id, elem)

        self.rendered = True

    def export_svg_content_layer(self, layer):
        """
        Function to export group content for a given layer to svg
        :param layer:
        :return:
        """

        if self.background is not None:
            pre_rect = '<rect width="%s" height="%s" style="fill:%s;" />'%(self.width,
             self.height, self.background)
        else:
            pre_rect = ''

        output = pre_rect + ''.join(self.content_layer[layer])

        return output

    def export_svg_layer(self, layer):

        out = '<g transform="translate(%s,%s)" class="%s" data-layer="%i">' % (self.positionner.x['final'],
                                                                               self.positionner.y['final'],
                                                                               self.name, layer)

        out += self.export_svg_content_layer(layer)

        if document._text_box:
            out += """<rect x="0"  y="0" width="%s" height="%s"
              style="stroke:#009900;stroke-width: 1;stroke-dasharray: 10 5;
              fill: none;" />""" % (self.positionner.width,
                                    self.positionner.height)

        if self.svg_decoration != '':
            out += self.svg_decoration.format(width=self.positionner.width,
                                              height=self.positionner.height)

        out += '</g>'

        return out
