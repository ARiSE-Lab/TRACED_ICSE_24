#include <string>
#include <vector>
#include <iostream>

int main()
{
    std::vector<int> ints;
    ints.push_back(1);
    ints.push_back(2);
    ints.push_back(3);
    std::vector<std::string>strs;
    strs.push_back("geh");
    std::string foo = "foo";
    foo += " boo";
    std::cout << foo << ints[0] << ints[1] << ints[2] << strs[0] << "\n";
}
