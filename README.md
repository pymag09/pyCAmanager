pyCAmanager
===========
  
  
Python CA Manager  
  
This simple, ready to use tool, helps you manage your own CA. It`s based on curses library and use python3.  
"caman.py" leads you through init procedure if you run it for a first time. Then caman.py will serve as a CA manager.  

Try it without installation with VirtualBox instance!!!  
https://www.dropbox.com/s/i7bih3clyl48cp6/pyCAmanager.tar.bz2?dl=0  
any user and password - ubuntu

DEPENDENCIES:  
    1) openssl  
    2) python3  

INSTALATION:  
    apt-get install openssl  
    caman.py create
    caman.py init
    edit openssl.cnf.  
        [ CA_default ]  
        dir=/path/where_certs_will_be_stored  
        new_certs_dir= $dir/signed_certs  
    edit subj.info
    run caman.py
  
ABOUT  
  
I use "caman.py" for radius and EAP. "caman.py" perform only manager actions but has hook functionality.. Here are three of them:  
1) "new.hook" is called after cert singing. It accepts three arguments CN(commcon name), email and days  
2) "revoke.hook" is called after cert revoking. It accepts three arguments cert file name, CN and email  
3) "crl.hook" is called after generating CRL. No arguments are avaliable for this hook  
You can use "crl.hook", for example, to transfer CRL to radius server.  
  
  
-------------------------------  
    #!/bin/bash  
      
      
    SCP=`which scp`  
    SSH=`which ssh`  
      
      
    ! /bin/cat $PKI_ROOT/cacert.pem $PKI_ROOT/crl.pem > $PKI_ROOT/cacrlcert.pem && exit 1  
    if [[ -e $PKI_ROOT/cacrlcert.pem ]]; then  
       $SCP $PKI_ROOT/cacrlcert.pem radius_admin@172.16.0.1:/home/putcert #transfering crl to radius  
       $SSH radadm@freeradius /home/radius_admin/radrestart.sh #restart radius  
    fi  
  
-------------------------------  
  
  
Pay attention to $PKI_ROOT environment variable. It must be set to folder where CA files is located, where you are going to store  
all neccessary files in particular self-signed cert, index.txt etc.  
  
  
"subj.info" file. 
  
All actions with certs require entering passwords and other information.  
"subj.info" contains information neccessary for creating cert request. "caman.py init" will create template: /OU=smth/O=Example Corp/C=SM/ST=Anything/L=My_place  
  
  
    CN: CommonName (mandatory)  
    OU: OrganizationalUnit (can be empty. you can delete it from "subj.info" if you want)  
    O: Organization (mandatory)  
    L: Locality (mandatory)  
    S: StateOrProvinceName (mandatory)  
    C: CountryName (mandatory)  
  
  
Keep in mind if you have problem with caman.py  
1) PKI_ROOT must be equal to [ CA_default ] dir= in openssl.conf. Try to keep them equal when you edit any of this pathes  
2) A first line of hook file must be the path to the relevant shell (for example #!/bin/bash)  
3) After initialization put openssl.conf file in PKI_ROOT folder
