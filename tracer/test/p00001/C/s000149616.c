#include <stdio.h>
int main(void)
{
	int a[10];
	int i;
	int MAX[3];
	for(i = 0; i < 10; i++)
	{
		scanf("%d", &a[i]);
	}
	for(i = 0; i < 3; i++)
	{
		MAX[i] = 0;
	}
	for(i = 0; i < 10; i++)
	{
		if(MAX[0] < a[i])
		{
			MAX[0] = a[i];
		}
	}
	for(i = 0; i < 10; i++)
	{
		if(MAX[1] < a[i])
		{
			if(a[i] < MAX[0])
			{
				MAX[1] = a[i];
			}
		}
	}
	for(i = 0; i < 10; i++)
	{
		if(MAX[2] < a[i])
		{
			if(a[i] < MAX[1])
			{
				MAX[2] = a[i];
			}
		}
	}
	for(i = 0; i < 3; i++)
	{
		printf("%d\n", MAX[i]);
	}
	return 0;
}