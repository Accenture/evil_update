#include <stdio.h>
#include <stdlib.h>
#include <openssl/md5.h>
#include <string.h>
#include <libxml/parser.h>
#include <libxml/tree.h>

//gcc -g -Wall -o sample_victim sample_victim.c -lssl -lcrypto -I/usr/include/libxml2 -lxml2

void getHashFromXML(char* buffer, const char *filename) {
    xmlParserCtxtPtr ctxt; /* the parser context */
    xmlDocPtr doc; /* the resulting document tree */
    xmlChar *key;
    xmlNode *cur = NULL;
    MD5_CTX mdContext;
    char d[3];
    int i;
    unsigned char c[MD5_DIGEST_LENGTH];
    char tmp_buffer[33];
    char char_hash[33];
    char sig_file_hash[33];

    /* create a parser context */
    ctxt = xmlNewParserCtxt();
    if (ctxt == NULL) {
        fprintf(stderr, "Failed to allocate parser context\n");
	return;
    }
    /* parse the file, activating the DTD validation option */
    doc = xmlCtxtReadFile(ctxt, filename, NULL, XML_PARSE_NOBLANKS);
    
    /* check if parsing succeeded */
    if (doc == NULL) {
        fprintf(stderr, "Failed to parse %s\n", filename);
    } else {
        cur = xmlDocGetRootElement(doc);
        cur = cur->children;
        
        while (cur != NULL) {
            if ((!xmlStrcmp(cur->name, (const xmlChar *)"sig"))) {
                key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
                strcpy(sig_file_hash,key);
                printf("[*] Found signature value of %s ... \n",sig_file_hash);
                xmlFree(key);
            }
            if ((!xmlStrcmp(cur->name, (const xmlChar *)"hash"))) {
                key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
                strcpy(tmp_buffer,key);
                printf("[*] Found data hash value of %s ... \n",tmp_buffer);
                xmlFree(key);
            }
            cur = cur->next;
        }
    }
    MD5_Init (&mdContext);
    MD5_Update(&mdContext, tmp_buffer, 32);
    MD5_Final(c,&mdContext);
    for(i = 0; i < MD5_DIGEST_LENGTH; i++) {
        sprintf(d,"%02x", c[i]);
        char_hash[i*2] = d[0];
        char_hash[i*2+1] = d[1];
    }
    for(i = 0; i < 32; i++) {
        if (char_hash[i] != sig_file_hash[i]){
            printf("[*] Siganture validation failed!\n");
            exit(1);
        }
    }
    printf("[*] Manifest file signature valid!\n");
    strncpy(buffer,tmp_buffer,32);
	    
    
	/* free up the resulting document */
	xmlFreeDoc(doc);
    /* free up the parser context */
    xmlFreeParserCtxt(ctxt);
}

int main(int argc, char** argv)
{
    unsigned char c[MD5_DIGEST_LENGTH];
    char ch;
    char *filename=argv[1];
    char *sig_filename = argv[2];
    char *out_filename = "sample_victim.output";
    int i;
    FILE *inFile = fopen(filename, "rb");
    FILE *sigFile = fopen(sig_filename,"r");
    FILE *outFile = fopen(out_filename,"a");
    MD5_CTX mdContext;
    int bytes;
    unsigned char data[1024];
    char d[3];
    char xml_hash[1024] = {0};
    char char_hash[1024];
    int matches = 1;

    memset(char_hash,0,1024);
    if (argc != 3) {
        printf("[*] Usage: %s <data_file> <signature_file>\n",argv[0]);
        return 0;
    }
    if (inFile == NULL || sigFile == NULL) {
        printf ("Either %s or %s can't be opened.\n", filename, sig_filename);
        return 0;
    }
    fclose(sigFile);
    // Calculate MD5 and convert it to hexstring
    printf("[*] Calculating MD5 hash of the \"%s\" file ... \n",filename);
    MD5_Init (&mdContext);
    while ((bytes = fread(data, 1, 1024, inFile)) != 0)
        MD5_Update(&mdContext, data, bytes);
    MD5_Final(c,&mdContext);
    for(i = 0; i < MD5_DIGEST_LENGTH; i++) {
        sprintf(d,"%02x", c[i]);
        char_hash[i*2] = d[0];
        char_hash[i*2+1] = d[1];
    }
    printf("[*] MD5 hash calculated: %s\n",char_hash);
    
    printf("[*] Verifying authenticity of the package hashes ... \n");
    getHashFromXML(xml_hash,sig_filename);
    matches = 1;
    for(i = 0; i < 32; i++) {
        if (char_hash[i] != xml_hash[i]){
            matches = 0;
            break;
        }
    }
    // If we have match write a file with the inFile contents
    if (matches == 1){
        printf("[*] Everything seems legit ... writing output to %s ... \n",out_filename);
        // HASH verified this should only happen when "signature" validation completed successfully
        if ( fseek(inFile, 0L, SEEK_SET) != 0 ) { 
            printf("[!] SEEK failed.\n");
            return 0;
        }
        //inFile = fopen(filename, "rb");
        ch = fgetc(inFile) ;
        while( ch != EOF) {
            fputc(ch,outFile);
            ch = fgetc(inFile);
	    if (feof(inFile))
		    break;
        }
        fclose(inFile);
    } else {
        // If the hash does not match just shout
        printf("[!] Data hash does not match the has mentioned in manifest! Not writing ANYTHING!\n");
    }
    fclose(outFile);
    return 0;
}
