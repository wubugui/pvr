#! /usr/bin/env python

# ------------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------------

import math
import os
import sys

from pvr import *

import pvr.cameras
import pvr.lights
import pvr.renderers

# ------------------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------------------

reduceRes  =    1
frustumRes =    V3i(2048 / reduceRes, 1556 / reduceRes, 200 / reduceRes)
camResMult =    1 / float(reduceRes)
lightResMult =  1 / float(reduceRes)

primType = Prim.Inst.Line

primParams = {
    # Per-point
    "density"                        : V3f(1, 2, 4) * 12,
    "radius"                         : 0.25, 
    # Base per-prim
    "instance_radius"                : 0.002, 
    "num_points"                     : 10000000, 
    "fill"                           : 1, 
    # Noise per-prim
    "density_noise_scale"            : V3f(0.5, 0.5, 0.1) * 2,
    "density_noise_octaves"          : 8.0,
    "density_noise_octave_gain"      : 0.75, 
    "density_noise_lacunarity"       : 1.92,
    "displacement_noise_scale"       : V3f(0.5, 0.5, 0.1),
    "displacement_noise_octaves"     : 8.0,
    "displacement_noise_octave_gain" : 0.5, 
    "displacement_noise_lacunarity"  : 1.92,
    "displacement_noise_amplitude"   : 0.3,
    "density_noise"                  : 1,    # Turns on density noise
    "displacement_noise"             : 1     # Turns on displacement noise
}

raymarcherParams = {
    "use_volume_step_length" : 1,
    "volume_step_length_multiplier" : 1.0, 
    "do_early_termination" : 1,
    "early_termination_threshold" : 0.01
}

RenderGlobals.setupMotionBlur(24.0, 0.5)

# ------------------------------------------------------------------------------
# Camera
# ------------------------------------------------------------------------------

# Default camera
camera = pvr.cameras.standard(1.0 / reduceRes)

# ------------------------------------------------------------------------------
# Modeler
# ------------------------------------------------------------------------------

# Create a single line in a Polygons object
numPoints = 100
lines = Polygons()
lineIdx = lines.addPolygon(numPoints)
lines.setIsClosed(lineIdx, False)
for i in range(0, numPoints):
    pIdx = lines.addPoint()
    lines.setVertex(lineIdx, i, pIdx)

# Create attributes on line
pointAttrs = lines.pointAttrs()
pRef       = pointAttrs.vectorAttrRef("P")
tRef       = pointAttrs.addVectorAttr("T", V3f(0.0))
nRef       = pointAttrs.addVectorAttr("N", V3f(0.0))

def pos(x):
    return V3f(x, math.sin(math.pi * x * 2 / 3) * 0.5, 0) * 1.4
def tangent(x):
    dx = 0.1
    Pnext = pos(x + dx)
    P = pos(x)
    return (Pnext - P).normalized()
def normal(x):
    T = tangent(x)
    return V3f(0, 0, 1).cross(T).normalized()
    
# Set per-point attributes
for i in range(0, numPoints):
    frac = i / float((numPoints - 1))
    x = -1.5 + frac * 3.0
    P = pos(x)
    N = normal(x)
    T = tangent(x)
    # Compute attribute values
    # radius = 0.05 + (1 + math.cos(math.pi * 4 * frac)) * 0.1
    density = (1 + math.sin(0.5 + math.pi * 16 * frac))
    # Set attribute values
    pointAttrs.setVectorAttr(pRef, i, P)
    pointAttrs.setVectorAttr(tRef, i, T)
    pointAttrs.setVectorAttr(nRef, i, N)

# Add the particles to a Geometry object
geo = Geometry()
geo.setPolygons(lines)

# Create the volumetric primitive
prim = primType()
prim.setParams(primParams)

# Create the Modeler
modeler = Modeler()
modeler.setMapping(Mapping.FrustumMappingType)
modeler.setDataStructure(DataStructure.SparseBufferType)
modeler.setSparseBlockSize(SparseBlockSize.Size16)
modeler.setCamera(camera)

# Add input to modeler
input = ModelerInput()
input.setGeometry(geo)
input.setVolumePrimitive(prim)
modeler.addInput(input)

# Prep for execution
modeler.updateBounds()
modeler.setResolution(frustumRes.x, frustumRes.y, frustumRes.z)

# Execute modeler
modeler.execute()

# ------------------------------------------------------------------------------
# Renderer
# ------------------------------------------------------------------------------

# Standard settings
renderer = pvr.renderers.standard(raymarcherParams)

# ------------------------------------------------------------------------------
# Scene setup
# ------------------------------------------------------------------------------

# Camera
renderer.setCamera(camera)

# Volumes
volume = VoxelVolume()
volume.setBuffer(modeler.buffer())
volume.addAttribute("scattering", V3f(1.0))
renderer.addVolume(volume)

# Lights
lights = pvr.lights.standardThreePoint(renderer, 1.0 / reduceRes)
for light in lights:
    renderer.addLight(light)

# ------------------------------------------------------------------------------
# Render and output result
# ------------------------------------------------------------------------------

# Execute render
renderer.printSceneInfo()
renderer.execute()

# Save result
baseName = os.path.basename(sys.argv[0])
renderer.saveImage(baseName.replace(".py", ".exr"))
renderer.saveImage(baseName.replace(".py", ".png"))

# ------------------------------------------------------------------------------

