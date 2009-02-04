#include <stdio.h>
#include "rotatingtree.h"

int Assert_fatal_error(char* msg, char* filename, int lineno)
{
  fprintf(stderr, "*** assertion failed ***\n");
  fprintf(stderr, "%s:%d: %s\n", filename, lineno, msg);
  exit(1);
  return 0;
}

#define Assert_fatal_msg(msg)  Assert_fatal_error(msg, __FILE__, __LINE__)
#define Assert(x) ((void)((x) || Assert_fatal_msg(#x)))


#define KEY_OF(i)    ((void*)(((i) * 1330111) & mask))

struct te_s {
  void* prevkey;
  int count;
};

static int myenumfn(rotating_node_t* node, void* arg)
{
  struct te_s* te = (struct te_s*) arg;
  if (te->count != 0)
    Assert(((char*) node->key) > ((char*) te->prevkey));
  te->prevkey = node->key;
  te->count++;
  return 0;
}

void test1(int count)
{
  rotating_node_t* root = EMPTY_ROTATING_TREE;
  rotating_node_t* nodes;
  int i, j, mask;
  struct te_s te;
  mask = 1;
  while (mask < count*2)
    mask = mask*2+1;
  printf("test1(%d)\n", count);
  nodes = (rotating_node_t*) malloc(count*sizeof(rotating_node_t));
  Assert(nodes != NULL);
  for (i=0; i<count; i++)
    {
      nodes[i].key = KEY_OF(i);
      RotatingTree_Add(&root, &nodes[i]);
    }
  for (j=7; j>=1; j--)
    {
      printf("get...\n");
      for (i=0; i<count/j; i++)
        {
          rotating_node_t* p = RotatingTree_Get(&root, KEY_OF(i));
          Assert(p != NULL);
          Assert(p == &nodes[i]);
          /* test missing keys */
          p = RotatingTree_Get(&root, KEY_OF(count+i));
          Assert(p == NULL);
        }
    }
  printf("enum\n");
  te.count = 0;
  RotatingTree_Enum(root, myenumfn, &te);
  Assert(te.count == count);
  printf("done\n");
  free(nodes);
}

int main()
{
  test1(10);
  test1(100);
  test1(1000);
  test1(10000);
  test1(100000);
  //test1(1000000);
  return 0;
}
