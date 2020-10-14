#include <iostream>
#include <unordered_map>
#include <vector>
#include <stdlib.h>
#include<sstream>
using namespace std;

int main(int argc, char **argv)
{
    printf("estou no código C++\n");

    if (argc != 4) {
        printf("Erro\n");
        return 1;
    }
    else {

    // --------------------------------------------------------------
    // receive the parameter passed in execution time
        
        // receiving the strings
        std::string source_str = argv[1];
        std::string target_str = argv[2];
        std::string link_str = argv[3];

        // creating vectors
        vector<int> source;
        vector<int> target;
        
        // SOURCE
        //create string stream from the string
        stringstream source_stream(source_str);
   
        while(source_stream.good()) {
            string substr;
            
            // get first string delimited by comma
            getline(source_stream, substr, ',');
            
            // convert string to int
            stringstream intSource(substr);
            int source_value = 0;
            intSource >> source_value;
            
            // put the value to vector
            source.push_back(source_value);
        }

        // TARGET
        //create string stream from the string
        stringstream target_stream(target_str);
   
        while(target_stream.good()) {
            string substr;
            
            // get first string delimited by comma
            getline(target_stream, substr, ',');
            
            // convert string to int
            stringstream intTarget(substr);
            int target_value = 0;
            intTarget >> target_value;
            
            // put the value to vector
            target.push_back(target_value);
        }

//        printf("\nOLHA O SOURCE AQUI: \n");
//        for (int i=0; i<source.size(); i++) {
//            printf("%d\n", source[i]);    
//        }

//        printf("\nOLHA O TARGET AQUI: \n");
//        for (int i=0; i<target.size(); i++) {
//            printf("%d\n", target[i]);    
//        }

//        printf("\n");
//        printf("SOURCE: %s\n", source_str.c_str());
//        printf("TARGET: %s\n", target_str.c_str());
//        printf("LINK: %s\n", link_str.c_str());

    // --------------------------------------------------------------
    // vector

        // create vector of int
        vector<int> v;

        // put values at the end of vector
        v.push_back(2);
        v.push_back(22)
;       v.push_back(222);
        v.push_back(2222);

        // erase last vector value
        v.pop_back();


        printf("%d\n", v[1]);

        // return vector size
//        cout << v.size() << endl;

        // for in vector size
//        for (int i=0; i< v.size(); i++) {
//            cout << "teste " << v[i] << endl;
//        }


       



    // --------------------------------------------------------------
    // unordere_map of int

        unordered_map<string, int> autonomous_system;

        autonomous_system["GeeksforGeeks"] = 10;
        autonomous_system["Practice"] = 20;
        autonomous_system["Contribute"] = 30;

        for (auto x : autonomous_system)
            cout << "-- " << x.first << " " << x.second << endl;

        cout << "** " << autonomous_system["GeeksforGeeks"] << endl;
        cout << "** " << autonomous_system["Practice"] << endl;
        cout << "** " << autonomous_system["Contribute"] << endl;

    // --------------------------------------------------------------
    // unordere_map of vector

        // create a unordered_map with an int (ASN) in its key and a vector of ASN peers in its value
        unordered_map<int, std::vector<int>> autonomous_system_dict;

        // put the vector with the ASN 1
        autonomous_system_dict[1] = v;

        // print
        for (int i: autonomous_system_dict[1]) {
            cout << i << endl;
        }

        std::unordered_map<int,std::string> names{
        {1,"John"},
        {3,"Geoff"},
        {2,"Parekh"},
        };


        //Iterating through the map
        for (auto kv : names)
        {
            std::cout << kv.first <<  " : " << kv.second << '\n';
        }

        return 0;
    }

}