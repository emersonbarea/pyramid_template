#!/bin/bash

#wc -l < find . -type f

filenames=$(find ./minisecbgp/ -type f)
result=0

while read line; 
do 

	result_temp=$(wc -l "${line}" | awk '{print $1}')
	result=$(($result+$result_temp))

done <<< "$filenames"
echo $result

