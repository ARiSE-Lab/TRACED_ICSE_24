#include <iostream>
#include <algorithm>
using namespace std;
int main()
{
    int A[10];
     for(int i=0;i<10;i++)
     cin >> A[i];
     sort(A,A+10);
     reverse(A,A+10);
     for(int i=0;i<3;i++)  cout << A[i] << endl;
     return 0;
}