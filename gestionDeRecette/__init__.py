# Driver MySQL : PyMySQL (pur Python, rien à compiler) se fait passer pour mysqlclient ("MySQLdb").
# Django exige mysqlclient >= 2.2.1 : on annonce la version correspondante.
# Ce paquet est importé avant le moteur de base de données, que ce soit via manage.py ou via wsgi.py.
import pymysql

pymysql.version_info = (2, 2, 7, "final", 0)
pymysql.install_as_MySQLdb()
