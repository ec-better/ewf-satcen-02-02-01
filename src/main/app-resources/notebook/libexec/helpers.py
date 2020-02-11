import gdal
import os 
import pandas as pd
import lxml.etree as etree
import osr 
from shapely.geometry import box
import requests



def get_original_identifier(url,username,api_key):
   
    req = requests.get(url,
                        auth = (username, api_key),
                        allow_redirects = True)
    
    root = etree.fromstring(req.content)
    
    original_identifier = root.xpath('/a:feed/a:entry/b:EarthObservation/d:metaDataProperty/d:EarthObservationMetaData/d:vendorSpecific/d:SpecificInformation/d:localValue/text()', 
                                      namespaces={'a':'http://www.w3.org/2005/Atom',
                                                  'b':'http://www.opengis.net/opt/2.1',
                                                  'd':'http://www.opengis.net/eop/2.1'})
    
    return original_identifier[0].split('.SAFE')[0]






def cog(input_tif, output_tif):
    
    translate_options = gdal.TranslateOptions(gdal.ParseCommandLine('-co TILED=YES ' \
                                                                    '-co COPY_SRC_OVERVIEWS=YES ' \
                                                                    '-co COMPRESS=LZW'))

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
   
    series['utm_zone'] = row['original_identifier'][39:41]
    series['latitude_band'] = row['original_identifier'][41]
    series['grid_square']  = row['original_identifier'][42:44]

    
    return pd.Series(series)

def get_band_path(row, band):
    
    ns = {'xfdu': 'urn:ccsds:schema:xfdu:1',
          'safe': 'http://www.esa.int/safe/sentinel/1.1',
          'gml': 'http://www.opengis.net/gml'}
    
    path_manifest = os.path.join(row['local_path'],
                                 row['original_identifier'] + '.SAFE', 
                                'manifest.safe')
    
    root = etree.parse(path_manifest)
    #print etree.tostring(root, pretty_print=True)
    bands = [band]

    for index, band in enumerate(bands):

        sub_path = os.path.join(row['local_path'],
                                row['original_identifier'] + '.SAFE',
                                root.xpath('//dataObjectSection/dataObject/byteStream/fileLocation[contains(@href,("%s%s")) and contains(@href,("%s")) ]' % (row['latitude_band'],
                                row['grid_square'], 
                                band), 
                                  namespaces=ns)[0].attrib['href'])
    
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



    
    
def create_rgb(in_mineral, out_rgb):
    
    translate_options = gdal.TranslateOptions(gdal.ParseCommandLine('-co COMPRESS=LZW '\
                                                                    '-ot UInt16 ' \
                                                                    '-a_nodata 256 ' \
                                                                    '-b 1 -b 2 -b 3 -b 4'))
                                                                    
    ds = gdal.Open(in_mineral, gdal.OF_READONLY)

    gdal.Translate(out_rgb, 
                   ds, 
                   options=translate_options)
