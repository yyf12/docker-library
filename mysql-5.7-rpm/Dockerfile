FROM foxchann/centos:7.4.1708

MAINTAINER Foxchan

RUN yum -y install libaio libaio-devel net-tools

#Copy mysql rpm packages

#COPY mysql-community-client-5.7.18-1.el7.x86_64.rpm /root
#COPY mysql-community-common-5.7.18-1.el7.x86_64.rpm /root
#COPY mysql-community-devel-5.7.18-1.el7.x86_64.rpm /root
#COPY mysql-community-libs-5.7.18-1.el7.x86_64.rpm /root
#COPY mysql-community-libs-compat-5.7.18-1.el7.x86_64.rpm /root
#COPY mysql-community-server-5.7.18-1.el7.x86_64.rpm /root

#Install mysql


ADD mysql-community.repo /etc/yum.repos.d/mysql-community.repo


#RUN cd /root &&  yum -y install mysql-community-server-5.7.18-1.el7.x86_64.rpm \
#                		mysql-community-client-5.7.18-1.el7.x86_64.rpm \
#				mysql-community-devel-5.7.18-1.el7.x86_64.rpm  \
#				mysql-community-common-5.7.18-1.el7.x86_64.rpm \
#				mysql-community-libs-5.7.18-1.el7.x86_64.rpm  \
#				mysql-community-libs-compat-5.7.18-1.el7.x86_64.rpm
RUN yum -y install mysql-community-server-5.7.18 \
		   mysql-community-client-5.7.18 \
		   mysql-community-common-5.7.18 \
		   mysql-community-libs-5.7.18 \
                   mysql-community-libs-compat-5.7.18 \
                   mysql-community-devel-5.7.18

RUN yum clean all

ENV DATA_DIR /var/lib/mysql

ADD my.cnf /etc/my.cnf

ADD supervisor_mysql.conf /etc/supervisor.conf.d/mysql.conf

COPY scripts /scripts

RUN chmod +x /scripts/start

ENTRYPOINT ["/scripts/start", "/usr/bin/supervisord", "-n", "-c", "/etc/supervisord.conf"]
