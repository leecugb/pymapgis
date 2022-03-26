"""
pymapgis.py
Provides reading support for mapgis *.wt,*.wl,*.wp geospatial vector files.
author: 1045105061@qq.com
version: 1.0
Compatible with Python versions 3.9
"""

__version__ = "1.0"

import struct
import pyproj
import os
import re
import pandas as pd
import geopandas as gpd
import numpy as np
import shapely
import datetime
import warnings

class Reader:
    def __init__(self,filepath):
        self.f=open(filepath,'rb')
        type_dict={'WMAP`D22':'POINT','WMAP`D23':'POLYGON','WMAP`D21':'LINE'}
        type=self.f.read(8).decode('gbk')
        if type not in ['WMAP`D22','WMAP`D23','WMAP`D21']:
            raise InvalidFileError()
        self.shapeType=type_dict[type]

        print(struct.unpack('1i',self.f.read(4))[0])
        data_start=struct.unpack('1i',self.f.read(4))[0]
        self.f.seek(data_start)
        self.head_1=self.f.read(10)
        self.head_2=self.f.read(10)
        self.head_3=self.f.read(10)
        self.head_4=self.f.read(10)
        self.head_5=self.f.read(10)
        self.head_6=self.f.read(10)
        self.head_7=self.f.read(10)
        self.head_8=self.f.read(10)
        self.head_9=self.f.read(10)
        self.head_10=self.f.read(10)
        self.filepath=filepath
        if type =='WMAP`D22':
            start,vol=struct.unpack('2i',self.head_3[:-2])
            self.__get_attr(start)
            self.__get_points()

        elif type =='WMAP`D21':
            start,vol=struct.unpack('2i',self.head_3[:-2])
            self.__get_attr(start)
            self.__get_lines()

        else:
            start,vol=struct.unpack('2i',self.head_10[:-2])
            self.__get_attr(start)
            self.__get_polygons()

        self.__get_geopandas()
    def __get_crs(self):
        self.f.seek(109)
        self.pro=ord(self.f.read(1))
        pro_dict={5:'tmerc',1:'utm',2:'aea',3:'lcc'}
        elli=ord(self.f.read(1))
        self.f.seek(143)
        self.sc=struct.unpack('1d',self.f.read(8))[0]
        ellip={
            1:'+ellps=krass +towgs84=15.8,-154.4,-82.3,0,0,0,0 +units=m +no_d',
            2:'+a=6378140 +b=6356755.288157528',
            7:'+datum=WGS84',
            9:'+ellps=WGS72',
            10:'+ellps=aust_SA +towgs84=-117.808,-51.536,137.784,0.303,0.446,0.234,-0.29',
            11:'+ellps=aust_SA +towgs84=-134,-48,149,0,0,0,0',
            16:'+ellps=krass',
            116:'+ellps=clrk80 +towgs84=-166,-15,204,0,0,0,0',
            'cgcs2000':'+ellps=GRS80',
        }
        if (elli not in ellip.keys()) or (self.sc==0):
            self.sc=1
            self.crs=''
            warnings.warn(self.filepath+':  no invalid crs detected')
            return
        if self.pro==5:

            self.sc=self.sc/1000
            self.f.seek(151)
            cl=struct.unpack('1d',self.f.read(8))[0]
            cl=int(str(cl).split('.')[0][:-4])+int( str(cl).split('.')[0][-4:-2])/60.0+int(str(cl).split('.')[0][-2:]  )/60.0/60
            self.crs=pyproj.CRS('+proj=tmerc'+' +lat_0=0 +lon_0='+str(cl)+' +k=1 +x_0=500000 +y_0=0 '+ellip[elli]+' +units=m +no_defs')
        elif self.pro == 0:

            self.crs=pyproj.CRS('+proj=longlat '+ellip[elli]+' +no_defs')

        elif (self.pro==2 or self.pro==3):   # Albers or Lambert


            self.sc=self.sc/1000
            self.f.seek(151)
            cl=struct.unpack('1d',self.f.read(8))[0]
            cl=int(str(cl).split('.')[0][:-4])+int( str(cl).split('.')[0][-4:-2])/60.0+int(str(cl).split('.')[0][-2:]  )/60.0/60

            self.f.seek(175)
            lat0=struct.unpack('1d',self.f.read(8))[0]   #standard latitude
            lat_0=int(str(lat0).split('.')[0][:-4])+int(str(lat0).split('.')[0][-4:-2])/60.0+int(str(lat0).split('.')[0][-2:])/60.0/60
            lat1=struct.unpack('1d',self.f.read(8))[0]   #first standard latitude
            lat_1=int(str(lat1).split('.')[0][:-4])+int(str(lat1).split('.')[0][-4:-2])/60.0+int(str(lat1).split('.')[0][-2:])/60.0/60
            lat2=struct.unpack('1d',self.f.read(8))[0]   #second standard latitude
            lat_2=int(str(lat2).split('.')[0][:-4])+int(str(lat2).split('.')[0][-4:-2])/60.0+int(str(lat2).split('.')[0][-2:])/60.0/60
            x_0=struct.unpack('1d',self.f.read(8))[0]
            y_0=struct.unpack('1d',self.f.read(8))[0]
            self.crs=pyproj.CRS('+proj='+pro_dict[self.pro]+' +lat_0='+str(lat_0)+' +lon_0='+str(cl)+' +lat_1='+
                                str(lat_1)+' +lat_2='+str(lat_2)+' +x_0='+str(x_0)+' +y_0='+str(y_0)+' '+ellip[elli]+' +units=m +no_defs')

    def __get_attr(self,start):
        self.f.seek(start)
        self.f.read(2)
        self.f.read(4) # date-created
        self.f.read(6)
        offset=struct.unpack('1i',self.f.read(4))[0] # attribute data offset from this section
        print(offset)
        self.f.read(4)
        self.f.read(4)
        self.f.read(128) # work directory path
        self.f.read(128)
        self.f.read(40)
        self.f.read(2)
        fields_n=struct.unpack('1h',self.f.read(2))[0] # the number of fields
        num=struct.unpack('1i',self.f.read(4))[0] # the number of records
        leng=struct.unpack('1h',self.f.read(2))[0] # the length of each record
        self.f.read(18)
        field_names=[] # list to store field names
        types=[] # list to store field types
        nums=[] # list to store the number of records
        offs=[] # list to store the offset of each field
        lens=[] # list to store the length of each field

        for i in range(fields_n):
            temp=self.f.read(20)
            try:
                temp_=temp.decode('gbk').strip('\x00')
            except UnicodeDecodeError as err:
                temp_= temp[:   int(re.search(r'in position (\d+)',str(err)).group(1))].decode('gbk')
            field_names.append(temp_)
            types.append(ord(self.f.read(1)))
            offs.append(struct.unpack('1i', self.f.read(4)))
            self.f.read(2)
            lens.append(struct.unpack('1h',self.f.read(2)))
            self.f.read(1)
            self.f.read(1)
            self.f.read(2)
            nums.append(struct.unpack('1h', self.f.read(2)))
            self.f.read(4)
        print(lens)
        temp=np.array(types)
        mask=(temp==0)|(temp==1)|(temp==2)|(temp==3)|(temp==4)|(temp==5)|(temp==6)|(temp==7)
        field_names=np.array(field_names)[mask]
        
        field_type_dict={0:'string',1:'byte',2:'short integer',3:'integer',4:'float',5:'double',6:'date',7:'time'}


        offs=[i[0] for i in offs]

        k1=offs.copy()
        k1.append(leng) 
        length=np.array([i[1]-i[0] for i in zip(k1[:-1],k1[1:])])[mask]
        self.fields=list(zip(field_names,[field_type_dict[i] for i in np.array(types)[mask]],length))


        self.f.read(leng)
        self.data=[]
        for i in range(num-1):
            a=self.f.read(leng)
            attr=[]
            for j in range(offs.__len__()):
                if j<offs.__len__()-1:
                    if types[j]==4:
                        attr.append(struct.unpack('1f',a[offs[j]:offs[j+1]])[0])
                    elif types[j]==3:
                        attr.append(struct.unpack('1i',a[offs[j]:offs[j+1]])[0])
                    elif types[j]==2:
                        attr.append(struct.unpack('1h',a[offs[j]:offs[j+1]])[0])
                    elif types[j]==1:
                        attr.append(ord(a[offs[j]:offs[j+1]]))
                    elif types[j]==5:
                        attr.append(struct.unpack('1d',a[offs[j]:offs[j+1]])[0])

                    elif types[j]==6:
                        temp=a[offs[j]:offs[j+1]]
                        attr.append(datetime.date(struct.unpack('1h',temp[:2])[0],temp[2],temp[3]))

                    elif types[j]==7:
                        temp=a[offs[j]:offs[j+1]]
                        attr.append(datetime.time ( temp[0],temp[1], *(lambda x:(np.int64(np.floor(x)),np.int64(1000000*(x-np.floor(x)))))(struct.unpack('1d',temp[2:])[0])))

                    elif types[j]==0:
                        temp=a[offs[j]:offs[j+1]]
                        try:
                            temp_=temp.decode('gbk').strip('\x00')
                        except UnicodeDecodeError as err:
                            temp_= temp[:int(re.search(r'in position (\d+)',str(err)).group(1))].decode('gbk')
                        attr.append(temp_)
                else:
                    if types[j]==4:
                        attr.append(struct.unpack('1f',a[offs[j]:])[0])
                    elif types[j]==3:
                        attr.append(struct.unpack('1i',a[offs[j]:])[0])
                    elif types[j]==2:
                        attr.append(struct.unpack('1h',a[offs[j]:])[0])
                    elif types[j]==1:
                        attr.append(ord(a[offs[j]:]))
                    elif types[j]==5:
                        attr.append(struct.unpack('1d',a[offs[j]:])[0])

                    elif types[j]==6:
                        temp=a[offs[j]:]
                        attr.append(datetime.date(struct.unpack('1h',temp[:2])[0],temp[2],temp[3]))

                    elif types[j]==7:
                        temp=a[offs[j]:]
                        attr.append(datetime.time ( temp[0],temp[1], *(lambda x:(np.int64(np.floor(x)),np.int64(1000000*(x-np.floor(x)))))(struct.unpack('1d',temp[2:])[0])        )         )
                    elif types[j]==0:
                        temp=a[offs[j]:]
                        try:
                            temp_=temp.decode('gbk').strip('\x00')
                        except UnicodeDecodeError as err:
                            temp_= temp[:int(re.search(r'in position (\d+)',str(err)).group(1))].decode('gbk')
                        attr.append(temp_)
            self.data.append(attr)
        self.data=pd.DataFrame(self.data)
        self.data.columns=field_names

    def __get_points(self):
        self.__get_crs()
        start,vol=struct.unpack('2i',self.head_1[:-2])
        self.f.seek(start)
        self.f.read(93)
        self.coords=[]
        for i in range(int(vol/93)-1):
            self.f.read(1) # 1 label
            self.f.read(2) #
            self.f.read(4)
            self.coords.append(struct.unpack('2d',self.f.read(16)))
            self.f.read(70)
        self.coords=np.array(self.coords)
        self.geom = [shapely.geometry.Point(xy*self.sc) for xy in self.coords]
    def __get_lines(self):
        self.__get_crs()
        start,vol=struct.unpack('2i',self.head_1[:-2])
        self.f.seek(start)
        k=vol/57
        self.f.read(57)
        points=[]
        points_off=[]
        for i in range(int(k)-1):
            self.f.read(10)
            points.append(struct.unpack('1i',self.f.read(4))[0])
            points_off.append(struct.unpack('1i',self.f.read(4))[0])
            self.f.read(39)
        start,vol=struct.unpack('2i',self.head_2[:-2])
        self.coords=[]
        for i in range(int(k)-1):
            self.f.seek(start+points_off[i])
            self.coords.append(struct.unpack('%sd'%(points[i]*2),self.f.read(points[i]*16)))
        self.geom = [shapely.geometry.LineString(np.array(i).reshape(-1,2)*self.sc) for i in self.coords]
        
        
        
  
        
        
    def __get_polygons(self):
        self.__get_crs()
        start,vol=struct.unpack('2i',self.head_1[:-2])
        self.f.seek(start)
        k=vol/57
        self.f.read(57)
        points=[]
        points_off=[]
        for i in range(int(k)-1):
            self.f.read(10)
            points.append(struct.unpack('1i',self.f.read(4))[0])
            points_off.append(struct.unpack('1i',self.f.read(4))[0])
            self.f.read(39)
        start,vol=struct.unpack('2i',self.head_2[:-2])
        self.coords=[]
        for i in range(int(k)-1):
            self.f.seek(start+points_off[i])
            self.coords.append(struct.unpack('%sd'%(points[i]*2),self.f.read(points[i]*16)))
        geom_ = [shapely.geometry.LineString(np.array(i).reshape(-1,2)*self.sc) for i in self.coords]
        
        start,vol=struct.unpack('2i',self.head_4[:-2])

        self.f.seek(start)
        self.f.read(24)
        temp=[]
        for i in range(int(vol/24.-1)):
            temp.append(struct.unpack('4i',self.f.read(16)))
            self.f.read(8)
        temp=np.array(temp)
        temp=np.hstack((temp,np.arange(temp.__len__()).reshape((-1,1))))
        print(temp)

     
        self.data = self.data.loc[np.array(list(set(temp[:,2:4].flatten())-{0}))-1]
       
     
        self.geom=[]

       
        for i in set(temp[:,2:4].flatten())-{0}:
            mask=(temp[:,2]==i)|(temp[:,3]==i)

            x=temp[mask]
      
            mask_=x[:,2]==i
            kk=x[mask_]
        
            t=kk[:,0].copy()
            kk[:,0]=kk[:,1]
            kk[:,1]=t
            x[mask_]=kk
        
            if x.__len__()==1:
                poly=list(geom_[x[0][-1]].coords)
                self.geom.append( shapely.geometry.Polygon(poly)   )
            else:
                m=[]
                for ii in x:
                    m.append(list(geom_[ii[-1]].coords))
                #get linerings
                lines=[]
                while m:
                    xx=[]
                    for ii in m:
                        xx.append(ii[0])
                        xx.append(ii[-1])

                    t=np.ones((xx.__len__(),xx.__len__()))*np.inf
                    for ii in range(xx.__len__()-1):
                        for j in range(ii+1,xx.__len__()):
                            t[ii,j]=np.abs(np.array(xx)[ii]-np.array(xx)[j]).max()
                    
                    x,y=np.argwhere(t==t.min())[0]
                    if np.ceil((x+1)/2)==np.ceil((y+1)/2):
                        lines.append(m[np.int64(np.ceil((x+1)/2))-1])
                        m.pop(np.int64(np.ceil((x+1)/2))-1)
                    else:
                        if (x+1)/2<np.ceil((x+1)/2):
                            m[np.int64(np.ceil((x+1)/2))-1]=m[np.int64(np.ceil((x+1)/2))-1][-1::-1]
    
                        if (y+1)/2<np.ceil((y+1)/2):
                            m[np.int64(np.ceil((x+1)/2))-1].extend(m[np.int64(np.ceil((y+1)/2))-1])
    
                        else:
                            m[np.int64(np.ceil((x+1)/2))-1].extend(m[np.int64(np.ceil((y+1)/2))-1][-1::-1])

                        m.pop(np.int64(np.ceil((y+1)/2))-1)            
                    
                    
                self.geom.append(   shapely.geometry.MultiPolygon(   get_multipolygons(lines)   ) )
                

    def __get_geopandas(self):


        self.geodataframe = gpd.GeoDataFrame(self.data, crs=self.crs, geometry=self.geom)
        self.bbox=np.array([self.geodataframe.bounds.minx.min(),self.geodataframe.bounds.miny.min(),self.geodataframe.bounds.maxx.max(),self.geodataframe.bounds.maxy.max()])
    def to_file(self,filepath,**kwargs):

        #geodataframe.to_json()
        #geodataframe.to_file('be.shp',encoding='utf-8')
        self.geodataframe.to_file(filepath,**kwargs)

    def __len__(self):
        return self.geom.__len__()
    def __str__(self):
        return("mapgis file Reader\n%s feature%s (type %s)" %(self.__len__(),(lambda x:'s' if x>1 else '')(self.__len__()),self.shapeType))



    def __del__(self):
        self.f.close()


        
        
    def __enter__(self):
        return self
    def __exit__(self,type,value,traceback):
        self.__del__()
        
        
class InvalidFileError(BaseException):
    def __init__(self):
        pass
    def __str__(self):
        return "can not detect the file's geometry type"
class InvalidDirectoryError(BaseException):
    def __init__(self):
        pass
class TopoError(BaseException):
    def __init__(self):
        pass
    def __str__(self):
        return "topo error in this wp file"
    
def get_multipolygons(lines):
    
    tt=np.zeros((lines.__len__(),lines.__len__()))
    for i in range(lines.__len__()):
        for j in range(lines.__len__()):
            if i==j:
                tt[i,j]=0
            else:
                try:
                    temp=shapely.geometry.Polygon( lines[i]  ).within(    shapely.geometry.Polygon( lines[j]  )     )
                except:
                    temp=np.array([shapely.geometry.Point(i).within( shapely.geometry.Polygon(lines[j])  ) for i in lines[i]]).any()
                if temp:
                    tt[i,j]=1
              
    level_0={}
    for i in range(tt.__len__()):
        if not (tt[i]==1).any():
            level_0[i]=[lines[i]]
    for i in range(tt.__len__()):
        if (tt[i]==1).sum()==1:
            level_0[np.argwhere(tt[i]==1)[0][0]].append(lines[i])
    if not ((tt==1).sum(1)==2).any():
        return [shapely.geometry.Polygon(i[0],i[1:]) for i in level_0.values()]
    else:
        temp= [shapely.geometry.Polygon(i[0],i[1:]) for i in level_0.values()]
        temp.extend(  get_multipolygones([ lines[i] for i in np.argwhere((tt==1).sum(1)>1).flatten()]   )  )
        return temp
