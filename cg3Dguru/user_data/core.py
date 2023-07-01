"""The user_data module creates and manages Maya attributes in a pythonic way

Adding and managing custom attributes in Maya through Maya's standard low
level functions such as addAttr() has a few drawbacks that this higher-level
module attempts to overcome. These noteable improvements include:

1. user_data handles all the back-end work of reading and writing
user_data.Base class attributes to Maya attributes. Programmers and
Tech-artists can simply search for their Python instances inside of a Maya
scene or on a given node and work with the results.

2. Attributes in the attributes editor are organized under a compound
attribute, making it easy for end-users to understand how blocks of
attributes related to one another.

3. Built-in versioning support. Outdated attributes can easily be
identified and updated to match their Python equivalent as code evolves. 
"""

__author__ = "Nathaniel Albright"
__email__ = "developer@3dcg.guru"
__version__ = 0.9.0

import pymel.core as pm

#Don't change _RECORDS_NAME unless your project really desires an alternative
#name for the life of all scripts and tools that leverage the user_data module.
#And remember to change whenever getting an updated version of the module.
_RECORDS_NAME      = 'DataRecords'
"""The name of the custom attr that tracks what data is on a node"""

_DEFAULT_NODE_TYPE = 'network'
"""The nodeType that will be created when creating a node for data storing"""

AUTO_UPDATE = False
"""Should versioning attempt to auto update.

Some studios may want outdated data to automatically update. Setting this to
True will mean outdated data will attempt to update when it's discovered.
User's can decide this on a per-class instance by overriding
pre_update_version().
"""


class VersionUpdateException(Exception):
    """Thrown when BaseData.update_version() errors"""
    pass


class Attr(object):
    """A Wrapper for Maya's attribute arguements"""
    
    data_types = set(['string', 'stringArray', 'matrix', 'fltMatrix',
                      'reflectanceRGB', 'spectrumRGB', 'float2', 'float3', 'double2',
                      'double3', 'long2', 'long3', 'short2', 'short3' 'doubleArray',\
                      'floatArray', 'Int32Array', 'vectorArray', 'nurbsCurve', 'nurbsSurface',\
                      'mesh', 'lattice', 'pointArray']
                     )
    """A list of attributeType names that are of type 'data'
    
    If an attr.attr_type is found in Attr.data_types then the 'dt' flag
    is automatically added to the args when creating the Maya attribute, else
    the 'at' flag is used.
    """
        
    def __init__(self, name, attr_type, *args, **kwargs):
        """The init func can take any arguments used in maya.cmds.addAttr()
                
        Users don't need to include the following flags:
        
        -longName or -ln : this is instead derived from the Attr.name.
        -attributeType or -at : this is determined by inspecting Attr.attr_type.
        -dataType or -dt : this is determined by inspecting Attr.attr_type.
        -parent or -p: Determined by the Compound class parent-child structure
        -numberOfChildren or -nc : Determined by the Compound class parent-child structure
        """
        
        self.name = name
        self.attr_type = attr_type
        self.args = args
        self._flags = kwargs
        self._clear_invalid_flags(self._flags)


    def _clear_invalid_flags(self, flags):
        invalid = [ 'longName', 'ln', 'attributeType', 'at', 'dataType', 'dt', 'p', 'parent', 'numberOfchildren', 'nc']
        for key in invalid:
            if key in flags:
                flags.pop(key)
        
        
        
class Compound(Attr):
    """An attribute class that contain children attributes.
    
    For any attributeType other than 'compound', users don't need to create
    the children attributes. For example: Compound("space", 'float3') will
    automatically create spaceX, spaceY, spaceZ
    """
    
    compound_types = {'compound':0,
                     'reflectance':3, 'spectrum':3,
                     'float2':2, 'float3':3,
                     'double2':2, 'double3':3,
                     'long2':2, 'long3':3,
                     'short2':2, 'short3':3
                    }
    """A Dict of valid compound attr types and how many children to auto-create"""
    
    
    def __init__(self, name, attr_type, children = [], make_elements = True, *args, **kwargs):
        super(Compound, self).__init__(name, attr_type, *args, **kwargs)
        
        if attr_type not in Compound.compound_types:
            pm.error('UserData Module: {0} is not a valid CompoundType.  Print Compound.CompoundTypes for valid list'.format(attr_type))
        
        self._target_size = Compound.compound_types[attr_type]
        self._children   = children
        
        if self._target_size and make_elements:
            if self._children:
                pm.error('UserData Module: {0} can\t use _MakeElements with Compound class, if you also supply children')
            
            self._make_elements()

    
    def _make_elements(self):
        #define suffix for children
        xyz = ['X', 'Y', 'Z']
        rgb = ['R', 'G', 'B']
        
        suffix = xyz
        if 'usedAsColor' in self._flags or 'uac' in self._flags or \
           self.attr_type == 'spectrum' or self.attr_type == 'reflectance':
            suffix = rgb
            
        #determine child type            
        type = 'double'
        if self.attr_type[0] == 'f':
            type = 'float'
        elif self.attr_type[0] == 'l':
            type = 'long'
        elif self.attr_type[0] == 's':
            type = 'short'
            
        #add children to compound
        for i in range(0, self._target_size):
            attr = Attr(self.name + suffix[i], type)
            self.add_child(attr)
        
        
    def count(self):
        """How many children does this attribute have?"""
        return len(self._children)
    
    
    def add_child(self, child):
        """Add an attribute to this Compound as a child"""
        
        if self._target_size and len(self._children) > self._target_size:
            pm.error('UserData Module: Compound instance has reach max allowed children')
            
        self._children.append(child)
        
        
    def get_children(self):
        """Return the internal list of children"""
        return self._children
        
        
    def validate(self):
        """Validate that the required number of children exist
        
        This only makes sense when the compound instance is one of the
        Compound.compound_types other than 'compound' and is called
        before attempting call addAttr()
        """
        
        valid_size = False
        if not self._target_size:
            valid_size = len(self._children) > 0
        else:
            valid_size = self.count() == self._target_size
            
        if not valid_size:
            pm.error('UserData Module: {0} does not have the required number of children'.format(self.attr_type))



def create_attr(name, attr_type):
    """a convience func returns an Attr() or Compound() based on the attr_type"""
    if attr_type in Compound.compound_types:
        return Compound(name, attr_type)
    else:
        return Attr(name, attr_type)
    


class Record(object):
    """The class name of any data added to the Maya node and its version info"""
    
    def __init__(self, attr):
        self._attr = attr
        self._name, str_version = attr.get().split(':')
        self._version = tuple(map(int, str_version.split('.')))
        

    @property
    def name(self):
        """The name of the BaseData Sub-class"""
        return self._name

        
    @property
    def version(self):
        """What version of the sub-class is this record"""
        return self._version
    
    
    @version.setter
    def version(self, value):
        """Updates the version information for this record"""
        self.attr.unlock()
        self._version = value
        name = '{0}:{1}'.format( self.name, self._get_version_string() )
        self.attr.set( name )
        self.attr.lock()  
        
        
    @property
    def attr(self):
        """Returns the Maya attribute that represents this record"""
        return self._attr
    
    
    def _get_version_string(self):
        return '.'.join(map(str, self._version))
    
    
    
class BaseData(object):
    """Represents data that the user wants to store as Maya attributes
    
    Users should inherit from this class and at a minimum override
    get_atttributes(). get_attributes should either be declared as
    @classmethod or @staticmethod
    
    The python class names will become a compound attribute of the same name.
    Users can override cls.get_default_flags() to determine how this class
    looks as an attribute in Maya or pass the flags in on init().
    
    The BaseData class is responsible for reading and writing Maya attributes,
    creating and editing records, as well as managing class versioning.
    
    Any object that has a block of BaseData attributes stored on it will also
    contain a data block name that matches user_data._RECORDS_NAME. Records
    are used for determing what BaseData sub-classes are being stored on a
    given node. If a record for a given class is missing from the records
    then the user_data module won't know that the data exists.
    """
    
    attributes = []
    """The attributes returned from get_atttributes()
    
    these attributes are stored at the class level so the data can be
    inspected and read without needing to create an instance of the class
    additionally, per instance variants doesn't make sense in the scheme
    of how data is stored    
    """
    
    _version = (0, 0, 0)
    """The current vesion of this class"""

    def __init__(self, *args, **kwargs):  
        super(BaseData,self).__init__(*args, **kwargs)
        
        flags = self.get_default_flags()
        flags.update( kwargs )
        self._clear_invalid_flags( flags )
        
        self._flags   = flags
        self._records = None
        self._node    = None
        
        self._init_class_attributes()


###----Versioning Methods----

    @classmethod
    def get_class_version(cls):
        return cls._version
    

    @classmethod
    def set_class_version(cls, version):
        cls._version = version
        
    @classmethod
    def get_version_string(cls):
        return '.'.join(map(str, cls.version))

    
    @property
    def version(self):
        return self.get_class_version()
        
        
    @version.setter
    def version(self, value):
        self.set_class_version(value)
        
        
        
###---Flag Methods----
        
    @staticmethod
    def _clear_invalid_flags(flags):
        invalid = [ 'longName', 'ln', 'attribute', 'at', 'dataType', 'dt', 'p', 'parent', 'numberOfchildren', 'nc']
        for key in invalid:
            if key in flags:
                flags.pop(key)    

        
    @classmethod
    def get_default_flags(cls):
        return {}
        
        
###----Record Methods-----

    def _add_data_to_records(self):
        if self._records:

            indices = self._records.getArrayIndices()
            if not indices:
                idx = 0
            else:
                idx = -1
                for i in range(0, indices[-1]):
                    if not i in indices:
                        idx = i
                        break
                    
                if idx == -1:
                    idx = indices[-1] + 1
            
            #concatenating the name and version is not as clean in code
            #(vs seperate attributes), but it makes end-user view from
            #the attribute editor clean while not taking up much UI space
            name = '{0}:{1}'.format( self.get_data_name(), self.get_version_string() )
            self._records[idx].set( name )
            self._records[idx].lock()
            
                  
    @staticmethod
    def _create_records(node):
        global _RECORDS_NAME
        pm.addAttr(node, ln = _RECORDS_NAME,  dt = 'string', m= True)
                          
       
    @classmethod     
    def _get_records(cls, node, force_add ):
        if not node:
            pm.error('UserData Module : Can\'t get records. node is None')
            
        has_records = pm.hasAttr(node, _RECORDS_NAME)
                
        if (not has_records) and force_add:
            cls._create_records( node )
            has_records = True
        
        if has_records:
            return node.attr(_RECORDS_NAME) #.records
        else:
            return None
        
 
    @classmethod
    def get_records(cls, node):
        return cls._get_records(node, False)
 

    @classmethod
    def _get_record_by_name(cls, node, data_name):
        records = cls._get_records(node, False)
        found_record = None
        if records:
            for i in records.getArrayIndices():
                record = records[i]
                if not record.get():
                    continue
                
                name, version = record.get().split(':')
                if name == data_name:
                    found_record = Record(record)
                    break
                
        return found_record           

    
    @classmethod
    def get_record_by_name(cls, node, data_name):
        return cls._get_record_by_name( node, data_name )
    
    
    @classmethod
    def get_record(cls, node):
        return cls._get_record_by_name( node, cls.get_data_name() )
                  
###----Attribute Methods----
 
    def _find_attr_conflicts(self):
        attr_names = self.get_attribute_names()  
        if 'multi' in self._flags or 'm' in self._flags:
            #I *believe* attributes that are part of a multi arg won't conflict.            
            attr_names = []       
        
        attr_names.append( self.get_data_name() )
        
        conflicts = []
        for attr_name in attr_names:
            if pm.hasAttr(self._node, attr_name):
                conflicts.append(attr_name)
                
        if conflicts:
            record_names = []
            for i in self._records.getArrayIndices():
                record = Record(self._records[i])
                record_names.append( record.name )            

            class_name = self.__class__.__name__
            errorMessage = 'UserData Attribute Conflict :: Attribute Name(s) : {0} from class "{1}" conflicts with one of these existing blocks of data : {2}'
            pm.error( errorMessage.format(conflicts, class_name, record_names) )
 
               
    def add_attr(self, attr, parent_name):
        if parent_name:
            attr._flags['parent'] = parent_name
           
        if isinstance(attr, Compound):
            attr.validate()
            pm.addAttr(self._node, ln = attr.name, at = attr.attr_type, nc = attr.count(), **attr._flags)
            for child in attr.get_children():
                self.add_attr(child, attr.name)
            
        elif attr.attr_type in Attr.data_types:
            pm.addAttr(self._node, ln = attr.name, dt = attr.attr_type, **attr._flags)             
        else:   
            pm.addAttr(self._node, ln = attr.name, at = attr.attr_type, **attr._flags)     
           
           
    @classmethod                   
    def _get_attribute_names(cls, attr, name_list):
        name_list.append(attr.name)
        if isinstance(attr, Compound):
            for child in attr.get_children():
                cls._get_attribute_names(child, name_list)
            
            
    @classmethod        
    def get_attribute_names(cls):
        """
        returns a flat list of all the attribute names of the class.attributes.
        """
        name_list = []
        cls._init_class_attributes()
            
        for attr in cls.attributes:
            cls._get_attribute_names(attr, name_list)
            
        return name_list

      
    @classmethod
    def _init_class_attributes(cls):
        if not cls.attributes:
            cls.attributes = cls.get_attributes()
        
        
        
    @classmethod
    def get_attributes(cls):
        pm.error( 'UserData Module: You\'re attempting to get attributes for class {0} that has no get_attributes() overridden'.format(cls.__name__) )       
       
       
       
###----Update Methods----

    def pre_update_version(self, old_data, old_version_number):
        """
        Overwrite : 
        """
        global AUTO_UPDATE
        return AUTO_UPDATE
     
      
    def update_version(self, old_data, old_version_number):
        #Copy the attribute values to a temporary node
        temp_node, data = self.create_node(name = 'TRASH', ss=True)
        name_list = self.get_attribute_names()
        try:
            pm.copyAttr(self._node, temp_node, at = name_list, ic = True, oc = True, values = True)
        except:
            #delete the tempNode
            pm.delete(temp_node)
            
            message = 'Please impliment custom update logic for class: {0}  oldVersion: {1}  newVersion: {2}'.format( self.get_data_name(), old_version_number, self.version)
            raise VersionUpdateException(message)
        
        #delete the attributes off the current node
        pm.deleteAttr( self._node, at = self.get_data_name() )
        
        #rebuild with the latest definition
        self._create_data()

        #transfer attributes back to original node
        pm.copyAttr(temp_node, self._node, at = name_list, ic = True, oc = True, values = True)  
        
        #delete the tempNode
        pm.delete(temp_node)
        
        return True

        
     
    def post_update_version(self, data, update_successful):
        """
        Overwrite : 
        """        
        pass
    
    
###----Data Methods----
    
    @classmethod
    def get_data_name(cls):
        """
        Overwrite : 
        """
        return cls.__name__
            
    
    def _create_data(self):     
        attrs = self.__class__.attributes
        long_name = self.get_data_name()
        pm.addAttr(self._node, ln = long_name, at = 'compound', nc = len( attrs ), **self._flags )

        for attr in attrs:
            self.add_attr(attr, long_name)       
         
        return self._node.attr(long_name)
        
        
           
    def post_create(self, data):
        """
        Overwrite : 
        """        
        pass
              
              
    
    def get_data(self, node, force_add = False):
        #should be cleared, but let's be sure.
        self._records = None
        self._node    = node
        
        record = self.get_record(node)
        
        if not record and force_add:
            #lets make sure the records data exists
            self._records = self._get_records(node, force_add = True)
            
        #If found make sure the data block doesn't need updating.
        if record:
            data_name = self.get_data_name() 
            record_version = record.version #.get()
            current_version = self.version
            
            #Attempt to updat the version
            if record_version < current_version:
                old_data = self._node.attr(data_name)
                
                if self.pre_update_version(old_data, record_version):
                    updated = self.update_version(old_data, record_version)
                    if updated:
                        record.version = current_version
                                
                    data = self._node.attr(data_name)
                    self.post_update_version( data, updated )

            
            data = self._node.attr(data_name)
                    
        #else, add the data to the node           
        elif force_add:
            self._find_attr_conflicts()
            data = self._create_data()
            self._add_data_to_records()
            self.post_create( data )
            
        else:
            data = None
            
        self._records = None        
        self._node    = None
        return data      
    
    
        
    def add_data(self, node):
        return self.get_data(node, force_add=True)


    def delete_data(self, node):   
        record = self.get_record(node)
        
        if record:
            record.attr.unlock()
            pm.removeMultiInstance(record.attr, b=True)
            pm.deleteAttr(node, at = self.get_data_name() )   
            

###----Misc Methods----
    
    @classmethod
    def create_node(cls, nodeType = _DEFAULT_NODE_TYPE, *args, **kwargs):
        pynode = pm.general.createNode(nodeType, **kwargs)
    
        if pynode:
            classInstance = cls()
            data = classInstance.get_data(pynode, force_add = True)
            
        return (pynode, data)   
    
    
    
    
    
    
class Utils(object):
    def __init__(self, *args, **kwargs):
        super(Utils, self).__init__(*args, **kwargs)
    
    
    @staticmethod
    def get_classes():
        classes = BaseData.__subclasses__()
        return classes
    
    
    @staticmethod
    def get_class_names():
        sub_classes = Utils.get_classes()
        class_names = {}
        for subclass in sub_classes:
            class_names[ subclass.get_data_name() ] = subclass
            
        return class_names

    
    @staticmethod
    def find_attribute_conflicts(error_on_conflict = True):
        conflicts = {}
        attrs = {}
        for subclass in Utils.get_classes():
            default_flags = subclass.GetDefaultFlags()
            
            #if the Class is going to be added with a mutli flag, then
            #there shouldn't be any conflicts with its attributes
            if 'm' in default_flags or 'multi' in default_flags:
                continue
            
            attribute_names = subclass.GetAttributeNames()
            for attr_name in attribute_names:
                if attr_name not in attrs:
                    attrs[attr_name] = [subclass.__name__]
                else:
                    attrs[attr_name].append(subclass.__name__)
                    
        for attr_name in attrs:
            classes = attrs[attr_name]
            
            if len(classes) > 1:
                conflicts[attr_name] = classes
                
        if conflicts:
            for attr_name in conflicts:
                classes = conflicts[attr_name]
                pm.warning( 'UserData.Utils :: Attr conflict. : "{0}" exists in classes: {1}'.format(attr_name, classes))
                
            if error_on_conflict:
                pm.error( 'UserData.Utils :: Found conflict between attribute names. See console for info.')
                
        return conflicts
    
    
    @staticmethod
    def get_nodes_with_data(data_class = None, *args, **kwargs):
        nodes = pm.ls(*args, **kwargs)
        nodes.sort()
        
        data_nodes = []
        for node in nodes:
            if data_class:
                records = BaseData.get_record_by_name( node, data_class.get_data_name() )
            else:
                records = BaseData.get_records(node)
                
            if records:
                data_nodes.append(node)
                
        return data_nodes
    
    
    @staticmethod
    def validate_version(*args, **kwargs):
        nodes = pm.ls(*args, **kwargs)
        
        classes= Utils.get_classes()
        
        for data_class in classes:
            instance = data_class()
            
            for node in nodes:
                #this forces a version check
                instance.get_data(node)

        
            
    
    

