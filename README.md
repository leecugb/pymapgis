# pymapgis: 一个开源mapgis文件系统转换工具包
mapgis矢量文件格式（``*.wt``，``*.wl``，``*.wp``）是由国内著名的GIS厂商-中地数码公司-研发的一套闭源矢量文件格式，是目前国内地学工程和科研领域最重要的矢量数据存储格式。随着近年来地质调查工作的转型升级，其对国民经济的支撑领域越来越广，与其他学科的交叉融合也越来越广泛、深入。在这种背景下，一种能够无损解析mapgis矢量文件空间数据的开源工具包愈发重要，对于地质空间数据交换，多源数据集成，及大数据挖掘等新形势下地调事业转型发展的现实需求具有积极意义。

# 应用示例
首先，导入该python包
```
>>> import pymapgis
``` 
### 打开mapgis矢量文件
#### 使用Reader类
为了读取Mapgis矢量文件，将矢量文件名称（含路径）作为初始化参数创建一个pymapgis.Reader
对象。
```
>>> f = pymapgis.Reader('boundary.wp')
```
OR
```
>>> f = pymapgis.Reader('./boundary.wp')
```
OR
```
>>> f = pymapgis.Reader('/home/user/data/boundary.wp')
```
#### 使用语境管理器
pymapgis.Reader类可以用作语境管理器，这样可以保证当数据读取结束时，
文件对象能被正确关闭。
```
>>> with pymapgis.Reader('boundary.wp') as f:
...    print(f)
mapgis file Reader
424 features (type POLYGON)
```
### 读取mapgis矢量文件元数据
mapgis矢量文件包含对其内置空间数据的描述信息，包括几何类型、坐标系、要素数量等。
```
>>> f.shapeType
'POLYGON'
>>> f.shapeType == 'POLYGON'
True
```
几何类型用‘POINT’、‘LINE’和‘POLYGON’三个字符串表示，分别代表点、线、面。pymapgis读取
mapgis矢量文件内的坐标系参数，并用pyproj.CRS类重构该坐标系。
```
>>> f.crs
<Bound CRS: +proj=longlat +ellps=krass +towgs84=15.8,-154.4,-8 ...>
Name: unknown
Axis Info [ellipsoidal]:
- lon[east]: Longitude (degree)
- lat[north]: Latitude (degree)
Area of Use:
- undefined
Coordinate Operation:
- name: Transformation from unknown to WGS84
- method: Position Vector transformation (geog2D domain)
Datum: Unknown based on Krassovsky, 1942 ellipsoid
- Ellipsoid: Krassovsky, 1942
- Prime Meridian: Greenwich
Source CRS: unknown
```
除此之外，pymapgis实现了对矢量文件中要素数量和几何边界范围的计算。
```
>>> len(f)
424
>>> f.bbox
array([109.52410754, 32.86447255, 109.73390947, 32.99358777])
```
### 读取空间几何数据
mapgis矢量文件的几何体是由锚点或暗含的弧线表征的点或形状的集合。pymapgis利用shapely.
geometry.Point/LineString/Polygon类来封装mapgis矢量文件的几何体。可以通过Reader对象
的geom属性得到mapgis矢量文件的几何体列表。
```
>>> f.geom
[<shapely.geometry.polygon.Polygon at 0x7ff41c386580>,
 <shapely.geometry.polygon.Polygon at 0x7ff41c3860a0>,
 <shapely.geometry.polygon.Polygon at 0x7ff41c3867c0>,
 <shapely.geometry.polygon.Polygon at 0x7ff41c3a4e50>,
 <shapely.geometry.polygon.Polygon at 0x7ff41cccebe0>,
....................................................
 <shapely.geometry.polygon.Polygon at 0x7ff41ccce2e0>]
```
### 读取空间属性数据
通过访问Reader对象的fields属性得到一个Python列表。其内元组按照（字段名称，字段类型，字段
长度（字节数））的形式组织mapgis矢量文件中的字段信息。
```
>>> f.fields
[('ID', 'integer', 4),
 ('面积', 'double', 8),
 ('周长', 'double', 8),
 ('CHFCAC', 'integer', 4),
 ('CHFCAA', 'string', 6),
 ('CHFCAD', 'string', 25),
 ('PKIIZ', 'string', 255)]
```
通过访问Reader对象的data属性得到一个pandas.DataFrame，保存mapgis矢量文件的每一条属性记录和对应的几何字段。
```
>>> f.data
      ID          面积  ...  CODE                                           geometry
0      1  397.147542  ...        MULTIPOLYGON (((521942.871 3982861.084, 521958...
1      2    0.527566  ...        POLYGON ((518381.897 3983835.693, 518493.591 3...
2      3  224.022108  ...        MULTIPOLYGON (((504026.062 3968021.240, 503959...
3      4    3.279094  ...        POLYGON ((538014.221 3968347.168, 538043.701 3...
4      5    1.863868  ...        MULTIPOLYGON (((541377.158 3965902.452, 541324...
..   ...         ...  ...   ...                                                ...
419  402    9.472218  ...        MULTIPOLYGON (((635869.587 3946393.858, 635913...
420  403    1.887504  ...        POLYGON ((639844.274 3946483.212, 639986.964 3...
421  404    2.363032  ...        POLYGON ((644606.727 3944653.431, 644777.543 3...
422  405    6.442735  ...        POLYGON ((648047.471 3946112.706, 648261.725 3...
423  406    1.269507  ...        POLYGON ((648908.735 3945710.199, 649105.676 3...

[424 rows x 11 columns]
```
### 文件转换
Pymapgis内部使用geopandas.GeoDataFrame类封装mapgis矢量文件中的空间数据，并借助其文件转换接口提供mapgis文件与其他文件转换功能。
```
>>> f.to_file('boundary.shp', encoding='utf-8')
>>> f.to_file('boundary.geojson', driver='GeoJson')
```
