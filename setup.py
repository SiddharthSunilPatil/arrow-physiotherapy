from setuptools import setup,find_packages
from typing import List

hypen_e_dot = '-e .'
def get_requirements(file_path:str)->List[str]:
    '''
    This function returns a list of requirements 

    '''
    requirements=[]
    with open(file_path) as file_obj:
        requirements=file_obj.readlines()
        requirements=[req.replace("\n","") for req in requirements]

        if hypen_e_dot in requirements:
            requirements.remove(hypen_e_dot)       

    return requirements
 
setup(
      name="Evodia_Tech_Physiotherapy_Location_Intelligence_Dashboard",
      version="0.1",
      author="Siddharth_patil",
      author_email="siddharth.vdipl@gmail.com",
      packages=find_packages(),
      install_requires=get_requirements('requirements.txt')
      )