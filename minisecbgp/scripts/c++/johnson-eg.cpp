#include <boost/config.hpp>
#include <fstream>
#include <iostream>
#include <vector>
#include <iomanip>
#include <boost/property_map/property_map.hpp>
#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/graphviz.hpp>
#include <boost/graph/johnson_all_pairs_shortest.hpp>
using namespace std;

int main(int argc, char **argv)
{
  using namespace boost;
  typedef adjacency_list<vecS, vecS, directedS, no_property,
    property< edge_weight_t, int, property< edge_weight2_t, int > > > Graph;

  stringstream intVertex_count(argv[2]);
  int vertex_count = 0;
  intVertex_count >> vertex_count;
  const int V = vertex_count;
  typedef std::pair < int, int >Edge;

  stringstream intEdge_array_length(argv[3]);
  int edge_array_length = 0;
  intEdge_array_length >> edge_array_length;
  Edge edge_array[edge_array_length];


  cout << "filename: " << argv[1] << endl;
  string link_filename = argv[1];
  string link_line;
    ifstream link_file (link_filename);
  if (link_file.is_open()) {
    cout << "estou no if" << endl;
    getline (link_file,link_line);
    link_file.close();
    stringstream link_stream(link_line);
    int edge_array_count = 0;
    while(link_stream.good()) {
      cout << "estou no while 1" << endl;
      string link_substr;
      getline(link_stream, link_substr, ',');
      stringstream as_stream(link_substr);
      int array_temp[2];
      int array_temp_index = 0;
      while(as_stream.good()) {
        cout << "estou no while 2" << endl;
        string as_substr;
        getline(as_stream, as_substr, '-');
        cout << as_substr << endl;
        stringstream intLink(as_substr);
        int link_value = 0;
        intLink >> link_value;
        array_temp[array_temp_index] = link_value;
        array_temp_index += 1;
      }
      edge_array[edge_array_count]=(Edge(array_temp[0], array_temp[1]));
      cout << array_temp[0] << "-" << array_temp[1] << endl;
      edge_array_count += 1;
    }
  }
  else {
    cout << "estou no else" << endl;
  }




  //edge_array[0]=(Edge(0, 1));
  //edge_array[1]=(Edge(0, 2));
  //edge_array[2]=(Edge(0, 3));
  //edge_array[3]=(Edge(0, 4));
  //edge_array[4]=(Edge(0, 5));
  //edge_array[5]=(Edge(1, 2));
  //edge_array[6]=(Edge(1, 5));
  //edge_array[7]=(Edge(1, 3));
  //edge_array[8]=(Edge(2, 4));
  //edge_array[9]=(Edge(2, 5));
  //edge_array[10]=(Edge(3, 2));
  //edge_array[11]=(Edge(4, 3));
  //edge_array[12]=(Edge(4, 1));
  //edge_array[13]=(Edge(5, 4));

  const std::size_t E = sizeof(edge_array) / sizeof(Edge);
#if defined(BOOST_MSVC) && BOOST_MSVC <= 1300
  // VC++ can't handle the iterator constructor
  Graph g(V);
  for (std::size_t j = 0; j < E; ++j)
    add_edge(edge_array[j].first, edge_array[j].second, g);
#else
  Graph g(edge_array, edge_array + E, V);
#endif

  property_map < Graph, edge_weight_t >::type w = get(edge_weight, g);
  int weights[edge_array_length];
  for (int i=0; i<=edge_array_length; i++) {
    weights[i] = 1;
  }
  int *wp = weights;

  graph_traits < Graph >::edge_iterator e, e_end;
  for (boost::tie(e, e_end) = edges(g); e != e_end; ++e)
    w[*e] = *wp++;

  std::vector < int >d(V, (std::numeric_limits < int >::max)());
  //int D[V][V];
  vector<vector<int> > D(V,vector<int>(V));
  johnson_all_pairs_shortest_paths(g, D, distance_map(&d[0]));

  std::cout << "       ";
  for (int k = 0; k < V; ++k)
    std::cout << std::setw(5) << k;
  std::cout << std::endl;
  for (int i = 0; i < V; ++i) {
    std::cout << std::setw(3) << i << " -> ";
    for (int j = 0; j < V; ++j) {
      if (D[i][j] == (std::numeric_limits<int>::max)())
        std::cout << std::setw(5) << "inf";
      else
        std::cout << std::setw(5) << D[i][j];
    }
    std::cout << std::endl;
  }
  return 0;
}