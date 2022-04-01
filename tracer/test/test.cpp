#include <iostream>
#include <string>
using namespace std;

int main(){
	int month, date;
	int c[11] = {31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30};
	string s[7] = {"Wednesday","Thursday","Friday","Saturday","Sunday","Monday","Tuesday"};
	while(cin >> month >> date && month){
		int t = date;
		for(int i = 0;i < month-1;i++)t += c[i];
		cout << s[t%7] << endl;
	}
	return 0; 
}