/* Rijndael Block Cipher

   Written by Mike Scott 21st April 1999
   mike@compapp.dcu.ie

   Copyright (c) 1999 Mike Scott

   See rijndael documentation. The code follows the documentation as closely
   as possible, and where possible uses the same function and variable names.

   Permission for free direct or derivative use is granted subject 
   to compliance with any conditions that the originators of the 
   algorithm place on its exploitation.  

   Inspiration from Brian Gladman's implementation is acknowledged.

   Written for clarity, rather than speed.
   Assumes long is 32 bit quantity.
   Endian indifferent.
   
   Further comments by Bram Cohen -
   
   The originators of Rijndael put no conditions on its use.
   
   I've hard-coded the block and key sizes, removed the decryption code, 
   gotten rid of the mutable globals, and made encrypt() put the 
   ciphertext in a different memory position than the plaintext.
   
   All changes to this Mike Scott's version are public domain.
   The authors disclaim all liability for any damages resulting from
   any use of this software.

*/

#define BYTE unsigned char       /* 8 bits  */
#define WORD unsigned long       /* 32 bits */

/* rotates x one bit to the left */

#define ROTL(x) (((x)>>7)|((x)<<1))

/* Rotates 32-bit word left by 1, 2 or 3 byte  */

#define ROTL8(x) (((x)<<8)|((x)>>24))
#define ROTL16(x) (((x)<<16)|((x)>>16))
#define ROTL24(x) (((x)<<24)|((x)>>8))

/* Fixed Data */

static BYTE fbsub[256];
static BYTE ptab[256],ltab[256];
static WORD ftable[256];
static WORD rco[30];
static BYTE fi[24];

/* Parameter-dependent data */

static WORD pack(BYTE *b)
{ /* pack bytes into a 32-bit Word */
    return ((WORD)b[3]<<24)|((WORD)b[2]<<16)|((WORD)b[1]<<8)|(WORD)b[0];
}

static void unpack(WORD a,BYTE *b)
{ /* unpack bytes from a word */
    b[0]=(BYTE)a;
    b[1]=(BYTE)(a>>8);
    b[2]=(BYTE)(a>>16);
    b[3]=(BYTE)(a>>24);
}

static BYTE xtime(BYTE a)
{
    BYTE b;
    if (a&0x80) b=0x1B;
    else        b=0;
    a<<=1;
    a^=b;
    return a;
}

static WORD SubByte(WORD a)
{
    BYTE b[4];
    unpack(a,b);
    b[0]=fbsub[b[0]];
    b[1]=fbsub[b[1]];
    b[2]=fbsub[b[2]];
    b[3]=fbsub[b[3]];
    return pack(b);    
}

BYTE ByteSub(BYTE x)
{
    BYTE y=ptab[255-ltab[x]];  /* multiplicative inverse */
    x=y;  x=ROTL(x);
    y^=x; x=ROTL(x);
    y^=x; x=ROTL(x);
    y^=x; x=ROTL(x);
    y^=x; y^=0x63;
    return y;
}

void gentables(void)
{ /* generate tables */
    int i, j, m;
    BYTE y,b[4];

  /* use 3 as primitive root to generate power and log tables */

    ltab[0]=0;
    ptab[0]=1;  ltab[1]=0;
    ptab[1]=3;  ltab[3]=1; 
    for (i=2;i<256;i++)
    {
        ptab[i]=ptab[i-1]^xtime(ptab[i-1]);
        ltab[ptab[i]]=i;
    }
    
  /* affine transformation:- each bit is xored with itself shifted one bit */

    fbsub[0]=0x63;
    for (i=1;i<256;i++)
    {
        y=ByteSub((BYTE)i);
        fbsub[i]=y;
    }

    for (i=0,y=1;i<30;i++)
    {
        rco[i]=y;
        y=xtime(y);
    }

  /* calculate forward tables */
    for (i=0;i<256;i++)
    {
        y=fbsub[i];
        b[3]=y^xtime(y); b[2]=y;
        b[1]=y;          b[0]=xtime(y);
        ftable[i]=pack(b);
    }
  /* pre-calculate forward increments */
    for (m=j=0;j<4;j++,m+=3)
    {
        fi[m]=(j+1)%4;
        fi[m+1]=(j+2)%4;
        fi[m+2]=(j+3)%4;
    }
}

void gkey(BYTE *key, WORD *fkey)
{ /* blocksize=32*4 bits. Key=32*4 bits */
  /* key comes as 4*4 bytes              */
  /* Key Scheduler. Create expanded encryption key */
    int i,j,k,N;
    WORD CipherKey[8];
    
    N=4*(10+1);
    
    for (i=j=0;i<4;i++,j+=4)
    {
        CipherKey[i]=pack((BYTE *)&key[j]);
    }
    for (i=0;i<4;i++) fkey[i]=CipherKey[i];
    for (j=4,k=0;j<N;j+=4,k++)
    {
        fkey[j]=fkey[j-4]^SubByte(ROTL24(fkey[j-1]))^rco[k];
        if (4<=6)
        {
            for (i=1;i<4 && (i+j)<N;i++)
                fkey[i+j]=fkey[i+j-4]^fkey[i+j-1];
        }
        else
        {
            for (i=1;i<4 &&(i+j)<N;i++)
                fkey[i+j]=fkey[i+j-4]^fkey[i+j-1];
            if ((j+4)<N) fkey[j+4]=fkey[j+4-4]^SubByte(fkey[j+3]);
            for (i=5;i<4 && (i+j)<N;i++)
                fkey[i+j]=fkey[i+j-4]^fkey[i+j-1];
        }
    }
}

/* There is an obvious time/space trade-off possible here.     *
 * Instead of just one ftable[], there could be 4, the other     *
 * 3 pre-rotated to save the ROTL8, ROTL16 and ROTL24 overhead */ 

void inline encrypt(BYTE *source, BYTE *buff, WORD *fkey)
{
    int i,j,k,m;
    WORD a[8],b[8],*x,*y,*t;
    for (i=0;i<16;i++)
    {
        buff[i] = source[i];
    }
    
    for (i=j=0;i<4;i++,j+=4)
    {
        a[i]=pack((BYTE *)&buff[j]);
        a[i]^=fkey[i];
    }
    k=4;
    x=a; y=b;

/* State alternates between a and b */
    for (i=1;i<10;i++)
    { /* 10 is number of rounds. */

/* if 4 is fixed - unroll this next 
   loop and hard-code in the values of fi[]  */

        for (m=j=0;j<4;j++,m+=3)
        { /* deal with each 32-bit element of the State */
          /* This is the time-critical bit */
            y[j]=fkey[k++]^ftable[(BYTE)x[j]]^
                 ROTL8(ftable[(BYTE)(x[fi[m]]>>8)])^
                 ROTL16(ftable[(BYTE)(x[fi[m+1]]>>16)])^
                 ROTL24(ftable[x[fi[m+2]]>>24]);
        }
        t=x; x=y; y=t;      /* swap pointers */
    }

/* Last Round - unroll if possible */ 
    for (m=j=0;j<4;j++,m+=3)
    {
        y[j]=fkey[k++]^(WORD)fbsub[(BYTE)x[j]]^
             ROTL8((WORD)fbsub[(BYTE)(x[fi[m]]>>8)])^
             ROTL16((WORD)fbsub[(BYTE)(x[fi[m+1]]>>16)])^
             ROTL24((WORD)fbsub[x[fi[m+2]]>>24]);
    }   
    for (i=j=0;i<4;i++,j+=4)
    {
        unpack(y[i],(BYTE *)&buff[j]);
        x[i]=y[i]=0;   /* clean up stack */
    }
    return;
}

/*
The rest of this file was written by Bram and Ross Cohen, and is public domain.
*/

#include "Python.h"

static PyObject *CounterMode_new(PyObject *self, PyObject *py_args);
static PyObject *CounterMode__call__(PyObject *py_self, PyObject *py_args);
static void CounterMode_dealloc(PyObject *py_self);
static inline void xor(BYTE *a, BYTE *b, BYTE *dest, int len);

typedef struct {
    PyObject_HEAD
    WORD fkey[120];
    BYTE pseudoBits[16];
    BYTE a0[16];
    int pseudoOffset;
} CounterModeObject;

staticforward PyTypeObject CounterMode_Type;

static PyObject *
CounterMode_new(PyObject *self, PyObject *py_args)
{
    int i;
    CounterModeObject *py_self;
    BYTE *key;
    int block_size;

    if (sizeof(WORD) != 4)
        return NULL;
    if (!PyArg_ParseTuple(py_args, "s#", &key, &block_size))
        return NULL;
    if (16 != block_size)
        return NULL;

    py_self = PyObject_New(CounterModeObject, &CounterMode_Type);
    gkey(key, py_self->fkey);
    py_self->pseudoOffset = 16;
    for (i = 0;i < 16;i++) {
        py_self->a0[i] = 0;
    }
    return (PyObject *)py_self;
}

static PyObject *
CounterMode__call__(PyObject *py_self, PyObject *py_args)
{
    BYTE *s, *dest;
    int s_len, len;
    PyObject *py_dest;
    BYTE *pseudoBits;
    int pseudoOffset;
    int index;
    BYTE *a0;
    
    CounterModeObject *self = (CounterModeObject *)py_self;
    pseudoBits = self->pseudoBits;
    pseudoOffset = self->pseudoOffset;
    a0 = self->a0;

    if (!PyArg_ParseTuple(py_args, "s#", &s, &s_len))
        return NULL;

    /* allocate a new uninitialized string for the ciphertext */
    py_dest = PyString_FromStringAndSize(NULL, s_len);
    dest = PyString_AsString(py_dest);

    /* use whatever leftover pseudo-random bits we have */
    len = 16-pseudoOffset;
    if (s_len <= len) {
        xor(s, pseudoBits+pseudoOffset, dest, s_len);
        self->pseudoOffset += s_len;
        return py_dest;
    }
    xor(s, pseudoBits+pseudoOffset, dest, len);
    dest += len; s += len; s_len -= len;

    while (1) {
        /* generate new bits */
        index = 15;
        while (++a0[index] == 0) {
            index--;
        }
        encrypt(a0, pseudoBits, self->fkey);
        if (s_len > 16) {
            xor(s, pseudoBits, dest, 16);
            dest += 16; s += 16; s_len -= 16;
        }
        else {
            xor(s, pseudoBits, dest, s_len);
            self->pseudoOffset = s_len;
            return py_dest;
        }
    }
}

static void
CounterMode_dealloc(PyObject *py_self)
{
    PyObject_Del(py_self);
}

static inline void
xor(BYTE *a, BYTE *b, BYTE *dest, int len)
{
    while(len--) {
        dest[len] = a[len] ^ b[len];
    }
}

static PyMethodDef StreamEncrypterMethods[] = {
    {"make_encrypter", CounterMode_new, METH_VARARGS},
    {NULL,             NULL}
};

statichere PyTypeObject CounterMode_Type = {
    /* The ob_type field must be initialized in the module init function
     * to be portable to Windows without using C++. */
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "CounterMode",             /*tp_name*/
    sizeof(CounterModeObject), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    /* methods */
    (destructor)CounterMode_dealloc, /*tp_dealloc*/
    0,                               /*tp_print*/
    0,                               /*tp_getattr*/
    0,                               /*tp_setattr*/
    0,                               /*tp_compare*/
    0,                               /*tp_repr*/
    0,                               /*tp_as_number*/
    0,                               /*tp_as_sequence*/
    0,                               /*tp_as_mapping*/
    0,                               /*tp_hash*/
    (ternaryfunc)CounterMode__call__,
};

DL_EXPORT(void)
init_StreamEncrypter(void)
{
    gentables();
    CounterMode_Type.ob_type = &PyType_Type;

    (void)Py_InitModule("_StreamEncrypter", StreamEncrypterMethods);
}

