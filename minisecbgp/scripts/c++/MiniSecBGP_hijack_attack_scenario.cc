#include <iostream>
#include <fstream>
#include <string>
#include <omp.h>
#include <vector>
#include<sstream>
#include <unordered_map>
using namespace std;

int main(int argc, char **argv)
{
    printf("estou no código C++\n");

    if (argc != 4) 
    {
        cout << "Usage: ./MiniSecBGP_hijack_attack_scenario.o source_filename target_filename link_filename" << endl;
        return 1;
    }
    else 
    {
        // id_as2_1:[agreement,id_link]
        typedef unordered_map<int, array<int, 2>> umap_id_as2; 
        // [id_as2_1:[agreement,id_link], id_as2_2:[agreement,id_link, id_as2_3:[agreement,id_link]
        typedef vector<umap_id_as2> vector_id_as2;
        // id_as1:[[id_as2_1:[agreement,id_link], id_as2_2:[agreement,id_link, id_as2_3:[agreement,id_link]]
        typedef unordered_map<int, vector_id_as2> umap_graph;
        umap_graph link;

        int tid;
        vector<int> source, target;
        string link_line;

        /* Fork a team of threads giving them their own copies of variables */
        #pragma omp parallel private(tid) 
        {
            
            tid = omp_get_thread_num();

            // source file
            if (tid == 0) 
            {
                cout << "comecei tid SOURCE" << endl;
                string source_filename = argv[1];
                string source_line;
                ifstream source_file (source_filename);
                if (source_file.is_open()) {
                    getline (source_file,source_line);
                    source_file.close();

                    stringstream source_stream(source_line);

                    while(source_stream.good()) {
                        string source_substr;
                        
                        getline(source_stream, source_substr, ',');
                        
                        stringstream intSource(source_substr);
                        int source_value = 0;
                        intSource >> source_value;
                        
                        source.push_back(source_value);
                    }   

                }
                else cout << "Unable to open file " << source_filename << endl;
                cout << "terminei tid SOURCE" << endl;
            }

            // target file
            if (tid == 1) 
            {
                cout << "comecei tid TARGET" << endl;
                string target_filename = argv[2];
                string target_line;
                ifstream target_file (target_filename);
                if (target_file.is_open()) {
                    getline (target_file,target_line);
                    target_file.close();

                    stringstream target_stream(target_line);

                    while(target_stream.good()) {
                        string target_substr;
                        
                        // get first string delimited by comma
                        getline(target_stream, target_substr, ',');
                        
                        // convert string to int
                        stringstream intTarget(target_substr);
                        int target_value = 0;
                        intTarget >> target_value;
                        
                        // put the value to vector
                        target.push_back(target_value);
                    }   

                }
                else cout << "Unable to open file " << target_filename << endl;
                cout << "terminei tid TARGET" << endl;
            }

            // link file
            if (tid == 2)
            {
                cout << "comecei tid LINK" << endl;
                string link_filename = argv[3];
                //string link_line;
                ifstream link_file (link_filename);
                if (link_file.is_open()) {
                    getline (link_file,link_line);
                    link_file.close();

                    stringstream link_stream(link_line);

                    while(link_stream.good()) {
                        string link_substr;
                        
                        // get first string delimited by comma
                        getline(link_stream, link_substr, ',');
                        
                        //cout << link_substr << endl;

                        stringstream as_stream(link_substr);

                        int array_temp[4];
                        int array_temp_index = 0;

                        while(as_stream.good()) {
                            string as_substr;
                            
                            // get first string delimited by hyphen
                            getline(as_stream, as_substr, '-');

                            // convert string to int
                            stringstream intLink(as_substr);
                            int link_value = 0;
                            intLink >> link_value;
                        
                            // put the value to vector
                            array_temp[array_temp_index] = link_value;
                            array_temp_index += 1;
                            
                        }

                        if (link.find(array_temp[0]) == link.end()) {
                            vector_id_as2 v_id_as2;
                            umap_id_as2 map2;
                            map2[array_temp[1]]={array_temp[2],array_temp[3]};
                            v_id_as2.push_back(map2);
                            link[array_temp[0]] = v_id_as2;
                        }
                        else {
                            vector_id_as2 v_id_as2;
                            vector_id_as2 id_as1_to_find = link[array_temp[0]];
                            for (const auto& my_umap_id_as2 : id_as1_to_find)
                                for (const auto& [my_inner_int, my_vector_ints] : my_umap_id_as2)
                                {
                                    umap_id_as2 map2;
                                    map2[my_inner_int]={my_vector_ints[0],my_vector_ints[1]};
                                    v_id_as2.push_back(map2);
                                }
                            umap_id_as2 map2;
                            map2[array_temp[1]]={array_temp[2],array_temp[3]};
                            v_id_as2.push_back(map2);
                            link[array_temp[0]] = v_id_as2;
                        }

                    }   

                }
                else cout << "Unable to open file " << link_filename << endl;
                cout << "terminei tid LINK" << endl;
            }
        }

        #pragma omp barrier

        cout << "terminei a barreira" << endl;

        /**
        printf("\nOLHA O SOURCE AQUI: \n");
        for (int i=0; i<source.size(); i++) {
            printf("%d\n", source[i]);    
        }

        printf("\nOLHA O TARGET AQUI: \n");
        for (int i=0; i<target.size(); i++) {
            printf("%d\n", target[i]);    
        }

        **/
        
        printf("\nOLHA O LINK AQUI: \n");
        for (const auto& [my_int, my_vector_id_as2] : link)
            for (const auto& my_umap_id_as2 : my_vector_id_as2)
                for (const auto& [my_inner_int, my_vector_ints] : my_umap_id_as2)
                {
                    std::cout << my_int << ":" << my_inner_int << ":";
                    for (int my_innermost_int : my_vector_ints)
                        std::cout << " " << my_innermost_int;
                    std::cout << '\n';
                }
        
        for (int i=0; i<source.size(); i++)
            cout << "vetor: " << source[i] << endl;
            
        cout << link[137055][0][67032][0] << endl;
        cout << link[137055][0][67032][1] << endl;
        //cout << link[137055][1][67032][0] << endl;
        // 137055:67032: 3 873704

        for (int i=0; i<link[137055][0][67032].size(); i++)
            cout << link[137055][0][67032][i] << endl;


        return 0;
    }
}