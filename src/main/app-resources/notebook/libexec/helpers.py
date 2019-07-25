import gdal
import os 
import pandas as pd
import lxml.etree as etree
import osr 
from shapely.geometry import box

def cog(input_tif, output_tif):
    
    translate_options = gdal.TranslateOptions(gdal.ParseCommandLine('-co TILED=YES ' \
                                                                    '-co COPY_SRC_OVERVIEWS=YES ' \
                                                                    ' -co COMPRESS=LZW'))

    ds = gdal.Open(input_tif, gdal.OF_READONLY)

    gdal.SetConfigOption('COMPRESS_OVERVIEW', 'DEFLATE')
    ds.BuildOverviews('NEAREST', [2,4,8,16,32])
    
    ds = None

    ds = gdal.Open(input_tif)
    gdal.Translate(output_tif,
                   ds, 
                   options=translate_options)
    ds = None

    os.remove('{}.ovr'.format(input_tif))
    os.remove(input_tif)

def analyse(row):
    
    series = dict()
   
    series['utm_zone'] = row['identifier'][39:41]
    series['latitude_band'] = row['identifier'][41]
    series['grid_square']  = row['identifier'][42:44]

    
    return pd.Series(series)

def get_band_path(row, band):
    
    ns = {'xfdu': 'urn:ccsds:schema:xfdu:1',
          'safe': 'http://www.esa.int/safe/sentinel/1.1',
          'gml': 'http://www.opengis.net/gml'}
    
    path_manifest = os.path.join(row['local_path'],
                                 row['identifier'] + '.SAFE', 
                                'manifest.safe')
    
    root = etree.parse(path_manifest)
    
    bands = [band]

    for index, band in enumerate(bands):

        sub_path = os.path.join(row['local_path'],
                                row['identifier'] + '.SAFE',
                                root.xpath('//dataObjectSection/dataObject/byteStream/fileLocation[contains(@href,("%s%s")) and contains(@href,("%s")) ]' % (row['latitude_band'],
                                row['grid_square'], 
                                band), 
                                  namespaces=ns)[0].attrib['href'][2:])
    
    return sub_path


def get_image_wkt(product):
    
    src = gdal.Open(product)
    ulx, xres, xskew, uly, yskew, yres  = src.GetGeoTransform()

    max_x = ulx + (src.RasterXSize * xres)
    min_y = uly + (src.RasterYSize * yres)
    min_x = ulx 
    max_y = uly

    source = osr.SpatialReference()
    source.ImportFromWkt(src.GetProjection())

    target = osr.SpatialReference()
    target.ImportFromEPSG(4326)

    transform = osr.CoordinateTransformation(source, target)

    result_wkt = box(transform.TransformPoint(min_x, min_y)[0],
                     transform.TransformPoint(min_x, min_y)[1],
                     transform.TransformPoint(max_x, max_y)[0],
                     transform.TransformPoint(max_x, max_y)[1]).wkt
    
    return result_wkt