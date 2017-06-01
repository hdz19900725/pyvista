"""
vtk plotting module 

"""
import colorsys

import vtk
from vtk.util import numpy_support as VN
import numpy as np

import vtkInterface

#==============================================================================
# Functions
#==============================================================================
def Plot(mesh, **args):
    """
    Convenience plotting function for a vtk object
    
    Includes extra argument 'screenshot', otherwise see :
    help(vtkInterface.PlotClass.AddMesh)
    
    """
    
    if 'screenshot' in args:
        filename = args['screenshot']
        del args['screenshot']
    else:
        filename = None

    if 'cpos' in args:
        cpos = args['cpos']
        del args['cpos']
    else:
        cpos = None

    # create plotting object and add mesh
    plobj = PlotClass()
    plobj.AddMesh(mesh, **args)
    
    # Set camera
    if cpos:
        print cpos
        plobj.SetCameraPosition(cpos)
        
    cpos = plobj.Plot(autoclose=False)
    
    # take screenshot
    if filename:
        plobj.TakeScreenShot(filename)

    # close and return camera position
    plobj.Close()
    del plobj
    return cpos


def CreateScalarBar(mapper, title=None):
    """ Creates scalar bar based on input mapper """
    
    # Create scalar bar
    scalarBar = vtk.vtkScalarBarActor()
    scalarBar.SetLookupTable(mapper.GetLookupTable())
      
    # Set properties
    scalarBar.GetTitleTextProperty().SetFontFamilyToCourier()
    scalarBar.GetTitleTextProperty().ItalicOff()
    scalarBar.GetTitleTextProperty().BoldOn()
    scalarBar.GetLabelTextProperty().SetFontFamilyToCourier()
    scalarBar.GetLabelTextProperty().ItalicOff()
    scalarBar.GetLabelTextProperty().BoldOn()
    scalarBar.SetNumberOfLabels(5)  
            
    if title:
        scalarBar.SetTitle(title)
        
    return scalarBar

#==============================================================================
# Classes
#==============================================================================
class PlotClass(object):
    """
    DESCRIPTION
    Plotting object to display vtk meshes or numpy arrays.

    
    EXAMPLE
    plobj = PlotClass()
    plobj.AddMesh(mesh, color='red')
    plobj.AddMesh(another_mesh, color='blue')
    plobj.Plot()
    del plobj
    
    """
    
    def __init__(self, off_screen=False):
        """ 
        DESCRIPTION
        Initialize a vtk plotting object
        
        
        INPUTS
        off_screen (bool, default False)
            When enabled, renders off screen.  Useful for automated screenshots
            
            
        OUTPUTS
        None
        
        """

        # Store setting
        self.off_screen = off_screen

        # Add FEM Actor to renderer window
        self.ren = vtk.vtkRenderer()
        
        self.renWin = vtk.vtkRenderWindow()
        self.renWin.AddRenderer(self.ren)
        
        if self.off_screen:
            self.renWin.SetOffScreenRendering(1)
            
        else:
            
            self.iren = vtk.vtkRenderWindowInteractor()
            self.iren.SetRenderWindow(self.renWin)
            
            # Allow user to interact
            istyle = vtk.vtkInteractorStyleTrackballCamera()
            self.iren.SetInteractorStyle(istyle)

        # Set background
        self.ren.SetBackground(0.3, 0.3, 0.3)
        
        # track objects
        self.objects = []
        
        self.frames = []

        # initialize image filter
        self.ifilter = vtk.vtkWindowToImageFilter()
        self.ifilter.SetInput(self.renWin)
        self.ifilter.SetInputBufferTypeToRGB()
        self.ifilter.ReadFrontBufferOff()
        
        # initialize movie type
        self.movietype = None


    def AddMesh(self, meshin, color=None, style='surface', scalars=None, 
                rng=None, stitle=None, showedges=True, psize=5.0, opacity=1,
                linethick=None, flipscalars=False, lighting=False, ncolors=1000,
                interpolatebeforemap=False, no_copy=False):
        """ 
        DESCRIPTION
        Adds a vtk unstructured, structured, or polymesh to the plotting object
        
        By default, the input mesh is copied on load.


        INPUTS
        meshin (vtk unstructured, structured, or polymesh)
            A vtk unstructured, structured, or polymesh.
            
        color (string or 3 item list, optional, defaults to white)
            Either a string, rgb list, or hex color string.  For example:
                color='white'
                color='w'
                color=[1, 1, 1]
                color='#FFFFFF'
            
        style (string, default 'surface')
            Visualization style of the vtk mesh.  One for the following:
                style='surface'
                style='wireframe'
                style='points'
                
        scalars (numpy array, default None)
            Scalars used to "color" the mesh.  Accepts an array equal to the
            number of cells or the number of points in the mesh.  Array should
            be sized as a single vector.
            
        rng (2 item list, default None)
            Range of mapper for scalars.  Defaults to minimum and maximum of
            scalars array.  Example: [-1, 2]
            
        stitle (string, default None)
            Scalar title.  By default there is no scalar legend bar.  Setting
            this creates the legend bar and adds a title to it.  To create a
            bar with no title, use an empty string (i.e. '').
            
        showedges (bool, default True)
            Shows the edges of a mesh.  Does not apply to a wireframe
            representation.
            
        psize (float, default 5.0)
            Point size.
            
        opacity (float, default 1)
            Opacity of mesh.  Should be between 0 and 1.
            
        linethick (float, default None)
            Thickness of lines.  Only valid for wireframe and surface
            representations.
            
        flipscalars (bool, default False)
            Flip scalar display approach.  Default is red is minimum and blue
            is maximum.
            
        lighting (bool, default False)
            Enable or disable Z direction lighting.
        
        ncolors (int, default 1000)
            Number of colors to use when displaying scalars.
        
        interpolatebeforemap (bool, default False)
            Enabling makes for a smoother scalar display.
        
        no_copy (bool, default False)
            Enabling forces the mesh to not to copy.  Faster, but adds 
            possibly unwanted extra scalars to the mesh.
            

        OUTPUTS
        mesh (vtk object)
            Pointer to added mesh (either copy or original)
            
        
        """
        
        # add convenience functions on load if not already loaded
        if not hasattr(meshin, 'Copy'):
            vtkInterface.AddFunctions(meshin)
        
        # select color
        if color is None:
            color = [1, 1, 1]
        elif type(color) is str or type(color) is unicode:
            color = vtkInterface.StringToRGB(color)
                
        # Create mapper
        self.mapper = vtk.vtkDataSetMapper()

        # copy grid on import for display purposes        
        if not no_copy:
            self.mesh = meshin.Copy()
        else:
            self.mesh = meshin
        
        #======================================================================
        # Scalar formatting
        #======================================================================
        if scalars is not None:
            # convert to numpy array
            if type(scalars) != np.ndarray:
                scalars = np.asarray(scalars)

            # ravel if not 1 dimentional            
            if scalars.ndim != 1:
                scalars = scalars.ravel()
                
            # Scalar interpolation approach
            if scalars.size == meshin.GetNumberOfPoints():
                self.mesh.AddPointScalars(scalars, '', True)
                self.mapper.SetScalarModeToUsePointData()
                self.mapper.GetLookupTable().SetNumberOfTableValues(ncolors)               
                if interpolatebeforemap:
                    self.mapper.InterpolateScalarsBeforeMappingOn()
    
            elif scalars.size == meshin.GetNumberOfCells():
                self.mesh.AddCellScalars(scalars, '')
                self.mapper.SetScalarModeToUseCellData()

            # Set scalar range
            if not rng:
                rng = [np.min(scalars), np.max(scalars)]
            elif type(rng) is float:
                rng = [-rng, rng]
                    
            if np.any(rng):
                self.mapper.SetScalarRange(rng[0], rng[1])
        
            # Flip if requested
            if flipscalars:
                self.mapper.GetLookupTable().SetHueRange(0.66667, 0.0)  
        else:
            self.mapper.SetScalarModeToUseFieldData()
        
        # Set mapper
        self.mapper.SetInputData(self.mesh)
        
        # Create Actor
        actor = vtk.vtkActor()
        actor.SetMapper(self.mapper)
        
        # select view style
        if style == 'wireframe':
            actor.GetProperty().SetRepresentationToWireframe()
        elif style == 'points':
            actor.GetProperty().SetRepresentationToPoints()
            actor.GetProperty().SetPointSize(psize)
        elif style =='surface':
            actor.GetProperty().SetRepresentationToSurface()
            
        # edge display style
        if showedges:
            actor.GetProperty().EdgeVisibilityOn()
        actor.GetProperty().SetColor(color)
        actor.GetProperty().SetOpacity(opacity)
        
        # lighting display style
        if lighting is False:
            actor.GetProperty().LightingOff()
        
        # set line thickness
        if linethick:
            actor.GetProperty().SetLineWidth(linethick) 
        
        # Add to renderer
        self.ren.AddActor(actor)
        
        # Add scalar bar if available
        if stitle is not None:
            self.scalarBar = CreateScalarBar(self.mapper, stitle)
            self.ren.AddActor(self.scalarBar)
            
        # return pointer to mesh
        return self.mesh


    def UpdateScalars(self, scalars, mesh=None, render=True):
        """ updates scalars of object (point only for now) 
        assumes last inputted mesh if mesh left empty
        """
        
        if mesh is None:
            mesh = self.mesh
            
        mesh.AddPointScalars(scalars, '', True)
        if render:
            self.Render()
            
            
    def UpdateCoordinates(self, points, mesh=None, render=True):
        """ updates points of object (point only for now) 
        assumes last inputted mesh if mesh left empty
        """
        if mesh is None:
            mesh = self.mesh
            
        # get pointer to array
#        pts_pointer = self.mesh.GetNumpyPoints()
#        pts_pointer[:] = points
        
        self.mesh.SetNumpyPoints(points)
        
        if render:
            self.Render()
            
    
    def Close(self):
        """ closes render window """

        if hasattr(self, 'renWin'):
            del self.renWin
        
        if hasattr(self, 'iren'):
            del self.iren
            
        if hasattr(self, 'textActor'):
            del self.textActor
            
        # end movie
        if hasattr(self, 'mwriter'):
            try:
                self.mwriter.close()
            except:
                pass
            

    def AddText(self, text, position=[10, 10], fontsize=50, color=[1, 1, 1],
                font='courier'):
        """ 
        Adds text to plot object
        
        font may be courier, times, or arial
        """
        self.textActor = vtk.vtkTextActor()
        self.textActor.SetPosition(position)
        self.textActor.GetTextProperty().SetFontSize(fontsize)
        self.textActor.GetTextProperty().SetColor(color)
        self.textActor.SetInput(text)
        self.AddActor(self.textActor)
        
        # Set font
        if font == 'courier':
            self.textActor.GetTextProperty().SetFontFamilyToCourier()
            
        elif font == 'times':
            self.textActor.GetTextProperty().SetFontFamilyToTimes()
            
        elif font == 'arial':
            self.textActor.GetTextProperty().SetFontFamilyToArial()          
            

    def OpenMovie(self, filename, framerate=24, codec='libx264', 
                  preset='medium'):
        """ Establishes a connection to the ffmpeg writer """
        
        # Attempt to load moviepy
        try:
            import moviepy.video.io.ffmpeg_writer as mwrite
        except:
            raise Exception('To use this feature install moviepy')
        
        # Create movie object and check if render window is active
        self.window_size = self.renWin.GetSize()
        if not self.window_size[0]:
            raise Exception('Run Plot first')
        
        self.mwriter = mwrite.FFMPEG_VideoWriter(filename, self.window_size, 
                                                 framerate, codec=codec,
                                                 preset=preset)
        
        self.movietype = 'mp4'
        
        
    def OpenGif(self, filename):
        try:
            import imageio
        except:
            raise Exception('To use this feature, install imageio')
        if filename[-3:] != 'gif':
            raise Exception('Unsupported filetype')
        self.mwriter = imageio.get_writer(filename, mode='I')
        
        
    def WriteFrame(self):
        """ Writes a single frame to the movie file """
        if self.movietype is 'mp4':
            self.mwriter.write_frame(self.GetImage())
        else:
            self.mwriter.append_data(self.GetImage())

        
    def GetImage(self):
        """ Returns an image array of current render window """
        window_size = self.renWin.GetSize()
        
        # Update filter and grab pixels
        self.ifilter.Modified()
        self.ifilter.Update()
        image = self.ifilter.GetOutput()
        img_array = vtkInterface.GetPointScalars(image, 'ImageScalars')
        
        # Reshape and write
        return img_array.reshape((window_size[1], window_size[0], -1))[::-1]


    def AddLines(self, lines, color=[1, 1, 1], width=5):
        """ Adds an actor to the renderwindow """
                
        if type(lines) is np.ndarray:
            lines = vtkInterface.MakeLine(lines)
        
        # Create mapper and add lines
        mapper = vtk.vtkDataSetMapper()
        vtkInterface.SetVTKInput(mapper, lines)
        
        # Create Actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetLineWidth(width); 
        actor.GetProperty().EdgeVisibilityOn()
        actor.GetProperty().SetEdgeColor(color)
        actor.GetProperty().SetColor(color)
        actor.GetProperty().LightingOff()
        
        # Add to renderer
        self.ren.AddActor(actor)
        

    def AddPoints(self, points, color=[1, 1, 1], psize=5, scalars=None, 
                  rng=None, name='', opacity=1, stitle='', flipscalars=False):
        """ Adds a point actor or numpy points array to plotting object """
        
        # Convert to points actor if "points" is a numpy array
        if type(points) == np.ndarray:
            pdata = MakeVTKPointsMesh(points)
            
        # Create mapper and add lines
        mapper = vtk.vtkDataSetMapper()
        vtkInterface.SetVTKInput(mapper, pdata)

        if np.any(scalars):
            vtkInterface.AddPointScalars(pdata, scalars, name, True)
            mapper.SetScalarModeToUsePointData()
        
            if not rng:
                rng = [np.min(scalars), np.max(scalars)]
                    
            if np.any(rng):
                mapper.SetScalarRange(rng[0], rng[1])       
                
            # Flip if requested
            if flipscalars:
                mapper.GetLookupTable().SetHueRange(0.66667, 0.0)                   
                
        # Create Actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetPointSize(psize); 
        actor.GetProperty().SetColor(color)
        actor.GetProperty().LightingOff()
        actor.GetProperty().SetOpacity(opacity)

        self.ren.AddActor(actor)
        
        
        # Add scalar bar
        if stitle:
            self.scalarBar = vtk.vtkScalarBarActor()
            self.scalarBar.SetLookupTable(mapper.GetLookupTable())
            
            self.scalarBar.GetTitleTextProperty().SetFontFamilyToCourier()
            self.scalarBar.GetTitleTextProperty().ItalicOff()
            self.scalarBar.GetTitleTextProperty().BoldOn()
            self.scalarBar.GetLabelTextProperty().SetFontFamilyToCourier()
            self.scalarBar.GetLabelTextProperty().ItalicOff()
            self.scalarBar.GetLabelTextProperty().BoldOn()
            
            self.scalarBar.SetTitle(stitle)
            self.scalarBar.SetNumberOfLabels(5)  
            
            self.ren.AddActor(self.scalarBar)
                
            
    def AddArrows(self, start, direction, mag=1):
        """ Adds arrows to plotting object """
        pdata = vtkInterface.CreateVectorPolyData(start, direction*mag)
        arrows = CreateArrowsActor(pdata)
        self.AddActor(arrows)

        return arrows
    
        
    def GetCameraPosition(self):
        """ Returns camera position of active render window """
        camera = self.ren.GetActiveCamera()
        pos = camera.GetPosition()
        fpt = camera.GetFocalPoint()
        vup = camera.GetViewUp()
        return [pos, fpt, vup]
        

    def SetCameraPosition(self, cameraloc):
        """ Set camera position of active render window """
        camera = self.ren.GetActiveCamera()
        camera.SetPosition(cameraloc[0])
        camera.SetFocalPoint(cameraloc[1]) 
        camera.SetViewUp(cameraloc[2])        
        

    def SetBackground(self, bcolor):
        """ Sets background color """
        self.ren.SetBackground(bcolor)
        
        
    def AddLegend(self, entries, bcolor=[0.5, 0.5, 0.5], border=False):
        """
        Adds a legend to render window.  Entries must be a list containing
        one string and color entry for each item
        """
        
        legend = vtk.vtkLegendBoxActor()
        legend.SetNumberOfEntries(len(entries))
        
        c = 0
        legendface = MakeLegendPoly()
        for entry in entries:
            legend.SetEntry(c, legendface, entry[0], entry[1])
            c += 1
        
        legend.UseBackgroundOn()
        legend.SetBackgroundColor(bcolor)
        if border:
            legend.BorderOn()
        else:
            legend.BorderOff()
        
        # Add to renderer
        self.ren.AddActor(legend)
        
        
    def Plot(self, title='', window_size=[1024, 768], interactive=True,
             autoclose=True):
        """ Renders """
        
        if title:
            self.renWin.SetWindowName(title)
            
        # size window
        self.renWin.SetSize(window_size[0], window_size[1])            
            
        # Render
        if interactive and (not self.off_screen):
            self.renWin.Render()
            self.iren.Initialize()
            self.iren.Start()
            
        else:
            self.renWin.Render()
        
        # Get camera position
        cpos = self.GetCameraPosition()
        
        if autoclose:
            self.Close()
            
        return cpos
    
        
    def AddActor(self, actor):
        """ Adds actor to render window """
        self.ren.AddActor(actor)
        
        
    def RemoveActor(self, actor):
        self.ren.RemoveActor(actor)
        
        
    def AddAxes(self):
        """ Add axes actor at origin """
        axesActor = vtk.vtkAxesActor()
        self.ren.AddActor(axesActor)
        
        # interactive axes appear broken as of 7.0
#        # create interactive axes        
#        axes = vtk.vtkOrientationMarkerWidget()
#        axes.SetOrientationMarker(axesActor)
#        axes.SetInteractor(self.iren)
#        axes.SetViewport(0.0, 0.0, 0.4, 0.4)
##        axes.On()
#        axes.SetEnabled(1)
#        axes.InteractiveOn()
#        self.ren.ResetCamera()
#        self.Render()
        
        
    def TakeScreenShot(self, filename=None):
        """
        Takes screenshot at current camera position
        """
        
        # attempt to import imsave for saving screenshots from vtk
        try:
            from scipy.misc import imsave
        except:
            raise Exception('To use scipy.misc.imsave install pip install pillow')

        # create inage filter        
        ifilter = vtk.vtkWindowToImageFilter()
        ifilter.SetInput(self.renWin)
        ifilter.SetInputBufferTypeToRGBA()
        ifilter.ReadFrontBufferOff()
        ifilter.Update()
        image = ifilter.GetOutput()
        origshape = image.GetDimensions()
        
        img_array = vtkInterface.GetPointScalars(image, 'ImageScalars')

        # overwrite background        
        background = self.ren.GetBackground()
        mask = img_array[:, -1] == 0
        img_array[mask, 0] = int(255*background[0])
        img_array[mask, 1] = int(255*background[1])
        img_array[mask, 2] = int(255*background[2])
        img_array[mask, -1] = 255
        
        mask = img_array[:, -1] != 255
        img_array[mask, -1] = 255
        
        img = img_array.reshape((origshape[1], origshape[0], -1))[::-1, :, :]
        if filename[-3:] == 'png':
            imsave(filename, img)
            
        elif filename[-3:] == 'jpg':
            imsave(filename, img[:, :, :-1])

        else:
            raise Exception('Only png and jpg supported')
            
        return img_array
            
            
    def Render(self):
        self.renWin.Render()

 
def MakeVTKPointsMesh(points):
    """ Creates a vtk polydata object from a numpy array """
    if points.ndim != 2:
        points = points.reshape((-1, 3))
        
    npoints = points.shape[0]
    
    # Make VTK cells array
    cells = np.hstack((np.ones((npoints, 1)), 
                       np.arange(npoints).reshape(-1, 1)))
    cells = np.ascontiguousarray(cells, dtype=np.int64)
    vtkcells = vtk.vtkCellArray()
    vtkcells.SetCells(npoints, VN.numpy_to_vtkIdTypeArray(cells, deep=True))
    
    # Convert points to vtk object
    vtkPoints = vtkInterface.MakevtkPoints(points)
    
    # Create polydata
    pdata = vtk.vtkPolyData()
    pdata.SetPoints(vtkPoints)
    pdata.SetVerts(vtkcells)
    
    return pdata
            

def CreateArrowsActor(pdata):
    """ Creates an actor composed of arrows """
    
    # Create arrow object
    arrow = vtk.vtkArrowSource()
    arrow.Update()
    glyph3D = vtk.vtkGlyph3D()
    glyph3D.SetSourceData(arrow.GetOutput())
    glyph3D.SetInputData(pdata)
    glyph3D.SetVectorModeToUseVector()
    glyph3D.Update()
    
    # Create mapper    
    mapper = vtk.vtkDataSetMapper()
    mapper.SetInputConnection(glyph3D.GetOutputPort())
    
    # Create actor
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().LightingOff()

    return actor
    
        
def PlotCurvature(mesh, curvtype='Gaussian', rng=None):
    """
    Plots curvature
    Availble options for curvtype:
        'Mean'
        'Gaussian'
        'Maximum  '  
    
    """
    
    # Get curvature values and plot
    c = vtkInterface.GetCurvature(mesh, curvtype)
    cpos = Plot(mesh, scalars=c, rng=rng, 
                stitle='{:s}\nCurvature'.format(curvtype))

    # Return camera posision
    return cpos

    
def PlotGrids(grids, wFEM=False):
    """
    Creates a plot of several grids as wireframes.  When wFEM is true, the first
    grid is a white solid
    """
    
    # Make grid colors
    N = len(grids)
    HSV_tuples = [(x*1.0/N, 0.5, 0.5) for x in range(N)]
    colors = map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples)
    
    pobj = PlotClass()
    for i in range(len(grids)):
        if not i and wFEM: # Special plotting for first grid
            pobj.AddMesh(grids[i])
        else:
            pobj.AddMesh(grids[i], color=colors[i], style='wireframe')
    
    # Render plot and delete when finished
    pobj.SetBackground([0.8, 0.8, 0.8])
    pobj.Plot(); del pobj


def PlotEdges(mesh, angle, width=10):
    """ Plots edges of a mesh """
    
    # Extract edge points from a mesh
    edges = vtkInterface.GetEdgePoints(mesh, angle, False)
        
    # Render
    pobj = PlotClass()
    pobj.AddLines(edges, [0, 1, 1], width)
    pobj.AddMesh(mesh)
    pobj.Plot(); del pobj
    
    
def PlotBoundaries(mesh):
    """ Plots boundaries of a mesh """
    featureEdges = vtk.vtkFeatureEdges()
    vtkInterface.SetVTKInput(featureEdges, mesh)
    
    featureEdges.FeatureEdgesOff()
    featureEdges.BoundaryEdgesOn()
    featureEdges.NonManifoldEdgesOn()
    featureEdges.ManifoldEdgesOff()
    
    edgeMapper = vtk.vtkPolyDataMapper();
    edgeMapper.SetInputConnection(featureEdges.GetOutputPort());
    
    edgeActor = vtk.vtkActor();
    edgeActor.GetProperty().SetLineWidth(5);
    edgeActor.SetMapper(edgeMapper)

    mapper = vtk.vtkDataSetMapper()
    vtkInterface.SetVTKInput(mapper, mesh)

    # Actor
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().LightingOff()    
        
    # Render
    pobj = PlotClass()
    pobj.AddActor(actor)
    pobj.AddActor(edgeActor)
    pobj.Plot(); del pobj
    
    
def MakeLegendPoly():
    """ Creates a legend polydata object """
    pts = np.zeros((4, 3))
    vtkpoints = vtkInterface.MakevtkPoints(pts)
    triangles = np.array([[4, 0, 1, 2, 3]])
    vtkcells = vtk.vtkCellArray()
    vtkcells.SetCells(triangles.shape[0],
                      VN.numpy_to_vtkIdTypeArray(triangles, deep=True))
                                                                     
    # Create polydata object
    mesh = vtk.vtkPolyData()
    mesh.SetPoints(vtkpoints)
    mesh.SetPolys(vtkcells)       

    return mesh                                  
                                                                     
                                                                     
